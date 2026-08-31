"""Solar Intelligence coordinator — refresh, backfill, training."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.db.solar_forecast_repo import SolarArrayRepository, SolarSiteConfigRepository, _to_domain_config
from energy_core.db.solar_intelligence_repo import (
    SolarHourlyForecastRepository,
    SolarModelRepository,
    SolarPerformanceDailyRepository,
    SolarProviderHealthRepository,
    SolarRadiationCacheRepository,
    SolarTrainingSampleRepository,
    SolarWeatherSnapshotRepository,
)
from energy_core.solar_forecast.rollup_queries import actual_kwh_for_day_resolved, hourly_to_readings
from energy_core.solar_intelligence.anomaly import compute_performance_daily
from energy_core.solar_intelligence.backfill import SolarBackfillService
from energy_core.solar_intelligence.calibration import SolarCalibrationService, should_promote_challenger
from energy_core.solar_intelligence.physical_model import PvArraySpec
from energy_core.solar_forecast.intelligence_bridge import persist_intelligence_v2_forecast
from energy_core.solar_intelligence.provider_factory import SolarIntelligenceProviderFactory
from energy_core.solar_intelligence.snapshot import local_today

logger = logging.getLogger(__name__)


class SolarIntelligenceCoordinator:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._factory = SolarIntelligenceProviderFactory(self._settings)
        self._calibration = SolarCalibrationService(self._settings)

    def _bundle_for(self, record) -> tuple:
        return self._factory.bundle_for(
            country_code=getattr(record, "country_code", None),
            latitude=record.latitude or 0.0,
            longitude=record.longitude or 0.0,
        )

    async def refresh_site(self, session: AsyncSession, site, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None or not record.enabled or not record.solar_intelligence_enabled:
            return False
        domain = _to_domain_config(record)
        if not domain.is_complete():
            return False

        bundle = self._bundle_for(record)
        health_repo = SolarProviderHealthRepository(session)
        model_repo = SolarModelRepository(session)
        champion = await model_repo.get_champion(site.id)

        try:
            forecast = await bundle.engine.generate(site=domain, champion=champion, now=now)
            await health_repo.record_success(site.id, bundle.radiation_name)
            await health_repo.record_success(site.id, bundle.weather_name)
        except Exception as exc:
            logger.exception("Solar intelligence refresh failed site=%s", site.slug)
            await health_repo.record_failure(site.id, bundle.radiation_name, str(exc))
            return False

        hourly_repo = SolarHourlyForecastRepository(session)
        await hourly_repo.replace_for_site(site.id, forecast)

        try:
            await persist_intelligence_v2_forecast(
                session,
                record,
                forecast,
                self._settings,
                open_meteo=self._factory.open_meteo_fallback.provider,
            )
        except Exception:
            logger.exception("Failed to persist v2 bridge forecast site=%s", site.id)

        try:
            to_ts = now + timedelta(hours=self._settings.solar_forecast_horizon_hours)
            rad = await bundle.radiation_provider.fetch_radiation(
                latitude=domain.latitude, longitude=domain.longitude, from_ts=now, to_ts=to_ts
            )
            wx = await bundle.weather_provider.fetch_weather(
                latitude=domain.latitude, longitude=domain.longitude, from_ts=now, to_ts=to_ts
            )
            await SolarRadiationCacheRepository(session).upsert_samples(site.id, rad)
            await SolarWeatherSnapshotRepository(session).upsert_snapshots(site.id, wx)
        except Exception:
            logger.debug("Radiation/weather cache skipped site=%s", site.id)

        await config_repo.touch_forecast(site.id)
        logger.info(
            "Solar intelligence forecast site=%s today=%.2f kWh status=%s provider=%s",
            site.id,
            forecast.expected_today_kwh,
            forecast.status,
            bundle.radiation_name,
        )
        return True

    async def run_backfill(self, session: AsyncSession, site, *, days: int = 60) -> int:
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None or not record.enabled:
            return 0
        domain = _to_domain_config(record)
        bundle = self._bundle_for(record)
        backfill = SolarBackfillService(
            radiation_provider=bundle.radiation_provider,
            weather_provider=bundle.weather_provider,
            open_meteo_fallback=self._factory.open_meteo_fallback,
        )
        since = datetime.now(UTC) - timedelta(days=days + 2)
        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)
        hourly = await reading_repo.list_hourly_rollups(site.id, from_time=since)
        raw = hourly_to_readings(hourly)
        if len(raw) < 48:
            readings = await reading_repo.list_readings(site.id, from_time=since, limit=10000)
            raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]

        array_repo = SolarArrayRepository(session)
        await array_repo.ensure_default_for_site(site.id, domain)
        arrays = await self._load_arrays(session, site.id, domain)

        to_day = local_today(site.timezone)
        from_day = to_day.fromordinal(to_day.toordinal() - days)
        samples = await backfill.backfill_site(domain, raw, from_day=from_day, to_day=to_day, arrays=arrays)
        repo = SolarTrainingSampleRepository(session)
        return await repo.upsert_samples(samples)

    async def train_model(self, session: AsyncSession, site) -> bool:
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None:
            return False
        domain = _to_domain_config(record)
        today = local_today(site.timezone)
        samples = await SolarTrainingSampleRepository(session).list_for_site(
            site.id, days=90, reference_date=today
        )
        challenger = self._calibration.train(
            site.id,
            samples,
            installed_kwp=domain.installed_peak_power_kw,
            tilt=domain.tilt_deg or 35.0,
            azimuth=domain.azimuth_deg or 180.0,
            training_to=today,
        )
        if challenger is None:
            return False
        model_repo = SolarModelRepository(session)
        await model_repo.save_challenger(challenger)
        champion = await model_repo.get_champion(site.id)
        if should_promote_challenger(champion, challenger):
            logger.info("Promoting solar intelligence challenger site=%s wape=%s", site.id, challenger.wape)
        return True

    async def update_performance_daily(self, session: AsyncSession, site, *, day: date, expected_kwh: float) -> None:
        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)
        actual, _ = await actual_kwh_for_day_resolved(
            reading_repo,
            site.id,
            day,
            timezone=site.timezone,
        )
        perf = compute_performance_daily(performance_date=day, actual_kwh=actual, expected_kwh=expected_kwh)
        await SolarPerformanceDailyRepository(session).upsert(site.id, perf)

    async def fetch_dmi_forecast(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[dict]:
        rows = await self._factory.dmi_client.fetch_rows(
            latitude=latitude,
            longitude=longitude,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return [
            {
                "timestamp": row["ts_utc"].isoformat(),
                "ghi_wm2": row.get("ghi_wm2"),
                "dhi_wm2": row.get("dhi_wm2"),
                "temperature_c": row.get("temperature_c"),
                "cloud_cover_pct": row.get("cloud_cover_pct"),
                "precipitation_mm": row.get("precipitation_mm"),
                "humidity_pct": row.get("humidity_pct"),
                "wind_speed_ms": row.get("wind_speed_ms"),
            }
            for row in rows
        ]

    async def _load_arrays(self, session, site_id: int, domain) -> list[PvArraySpec]:
        from sqlalchemy import select
        from energy_core.db.models import SolarArrayModel

        stmt = select(SolarArrayModel).where(SolarArrayModel.site_id == site_id)
        rows = await session.scalars(stmt)
        specs = [
            PvArraySpec(
                name=r.name,
                capacity_kwp=r.capacity_kwp,
                tilt_deg=r.tilt_degrees,
                azimuth_deg=r.azimuth_degrees,
            )
            for r in rows
        ]
        if not specs:
            specs = [
                PvArraySpec(
                    name="Main",
                    capacity_kwp=domain.installed_peak_power_kw,
                    tilt_deg=domain.tilt_deg or 35.0,
                    azimuth_deg=domain.azimuth_deg or 180.0,
                )
            ]
        return specs
