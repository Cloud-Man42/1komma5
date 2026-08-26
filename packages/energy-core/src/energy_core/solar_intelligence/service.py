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
from energy_core.solar_forecast.daily_evaluation import actual_kwh_for_day
from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_intelligence.anomaly import compute_performance_daily
from energy_core.solar_intelligence.backfill import SolarBackfillService
from energy_core.solar_intelligence.calibration import SolarCalibrationService, should_promote_challenger
from energy_core.solar_intelligence.engine import SolarIntelligenceEngine
from energy_core.solar_intelligence.physical_model import PvArraySpec
from energy_core.solar_intelligence.providers.open_meteo_adapter import OpenMeteoAdapter
from energy_core.solar_intelligence.providers.smhi_snow import SmhiSnowWeatherProvider
from energy_core.solar_intelligence.providers.smhi_strang import SmhiStrangRadiationProvider

logger = logging.getLogger(__name__)


class SolarIntelligenceCoordinator:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        om = OpenMeteoWeatherProvider(
            base_url=self._settings.open_meteo_base_url,
            historical_url=self._settings.open_meteo_historical_url,
            api_key=self._settings.open_meteo_api_key or None,
            timeout_seconds=self._settings.open_meteo_timeout_seconds,
        )
        fallback = OpenMeteoAdapter(om)
        self._strang = SmhiStrangRadiationProvider(
            base_url=self._settings.smhi_strang_base_url,
            timeout_seconds=self._settings.smhi_timeout_seconds,
        )
        self._snow = SmhiSnowWeatherProvider(
            base_url=self._settings.smhi_snow_base_url,
            timeout_seconds=self._settings.smhi_timeout_seconds,
        )
        self._engine = SolarIntelligenceEngine(
            radiation_provider=self._strang,
            weather_provider=self._snow,
            open_meteo_fallback=fallback,
            horizon_hours=self._settings.solar_forecast_horizon_hours,
        )
        self._backfill = SolarBackfillService(
            radiation_provider=self._strang,
            weather_provider=self._snow,
            open_meteo_fallback=fallback,
        )
        self._calibration = SolarCalibrationService(self._settings)

    async def refresh_site(self, session: AsyncSession, site, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None or not record.enabled or not record.solar_intelligence_enabled:
            return False
        domain = _to_domain_config(record)
        if not domain.is_complete():
            return False

        health_repo = SolarProviderHealthRepository(session)
        model_repo = SolarModelRepository(session)
        champion = await model_repo.get_champion(site.id)

        try:
            forecast = await self._engine.generate(site=domain, champion=champion, now=now)
            await health_repo.record_success(site.id, "smhi-strang")
            await health_repo.record_success(site.id, "smhi-snow")
        except Exception as exc:
            logger.exception("Solar intelligence refresh failed site=%s", site.slug)
            await health_repo.record_failure(site.id, "smhi-strang", str(exc))
            return False

        hourly_repo = SolarHourlyForecastRepository(session)
        await hourly_repo.replace_for_site(site.id, forecast)

        # Cache radiation/weather for admin coverage views
        try:
            to_ts = now + timedelta(hours=self._settings.solar_forecast_horizon_hours)
            rad = await self._strang.fetch_radiation(
                latitude=domain.latitude, longitude=domain.longitude, from_ts=now, to_ts=to_ts
            )
            wx = await self._snow.fetch_weather(
                latitude=domain.latitude, longitude=domain.longitude, from_ts=now, to_ts=to_ts
            )
            await SolarRadiationCacheRepository(session).upsert_samples(site.id, rad)
            await SolarWeatherSnapshotRepository(session).upsert_snapshots(site.id, wx)
        except Exception:
            logger.debug("Radiation/weather cache skipped site=%s", site.id)

        await config_repo.touch_forecast(site.id)
        logger.info(
            "Solar intelligence forecast site=%s today=%.2f kWh status=%s",
            site.id,
            forecast.expected_today_kwh,
            forecast.status,
        )
        return True

    async def run_backfill(self, session: AsyncSession, site, *, days: int = 60) -> int:
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None or not record.enabled:
            return 0
        domain = _to_domain_config(record)
        since = datetime.now(UTC) - timedelta(days=days + 2)
        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)
        readings = await reading_repo.list_readings(site.id, from_time=since, limit=100000)
        raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]

        array_repo = SolarArrayRepository(session)
        await array_repo.ensure_default_for_site(site.id, domain)
        arrays = await self._load_arrays(session, site.id, domain)

        to_day = date.today()
        from_day = to_day.fromordinal(to_day.toordinal() - days)
        samples = await self._backfill.backfill_site(domain, raw, from_day=from_day, to_day=to_day, arrays=arrays)
        repo = SolarTrainingSampleRepository(session)
        return await repo.upsert_samples(samples)

    async def train_model(self, session: AsyncSession, site) -> bool:
        config_repo = SolarSiteConfigRepository(session)
        record = await config_repo.get(site.id, timezone=site.timezone)
        if record is None:
            return False
        domain = _to_domain_config(record)
        samples = await SolarTrainingSampleRepository(session).list_for_site(site.id, days=90)
        challenger = self._calibration.train(
            site.id,
            samples,
            installed_kwp=domain.installed_peak_power_kw,
            tilt=domain.tilt_deg or 35.0,
            azimuth=domain.azimuth_deg or 180.0,
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
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
        readings = await reading_repo.list_readings(site.id, from_time=day_start - timedelta(days=1), limit=50000)
        raw = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
        actual, _ = actual_kwh_for_day(raw, day, site.timezone)
        perf = compute_performance_daily(performance_date=day, actual_kwh=actual, expected_kwh=expected_kwh)
        await SolarPerformanceDailyRepository(session).upsert(site.id, perf)

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
