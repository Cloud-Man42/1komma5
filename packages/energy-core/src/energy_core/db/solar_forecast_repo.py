"""Solar forecast persistence repositories."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    SolarArrayModel,
    SolarForecastEvaluationModel,
    SolarForecastModelProfileModel,
    SolarForecastObservationModel,
    SolarForecastPointModel,
    SolarForecastRunModel,
    SolarSiteConfigurationModel,
    SolarSiteConfigurationVersionModel,
    SolarSitePerformanceProfileModel,
    SolarWeatherCacheModel,
)
from energy_core.solar_forecast.types import (
    ForecastEvaluation,
    ModelState,
    SitePerformanceProfile,
    SolarForecast,
    SolarForecastModelProfile,
    SolarForecastObservation,
    SolarForecastPoint,
    SolarSiteConfiguration,
    WeatherForecast,
    WeatherForecastPoint,
)


@dataclass(frozen=True, slots=True)
class SolarConfigRecord:
    site_id: int
    latitude: float | None
    longitude: float | None
    installed_peak_power_kw: float | None
    azimuth_deg: float | None
    tilt_deg: float | None
    inverter_max_power_kw: float | None
    system_loss_percent: float
    enabled: bool
    tilt_estimated: bool
    azimuth_estimated: bool
    timezone: str
    solar_intelligence_enabled: bool = False


def _to_domain_config(record: SolarConfigRecord) -> SolarSiteConfiguration:
    return SolarSiteConfiguration(
        site_id=record.site_id,
        latitude=record.latitude or 0.0,
        longitude=record.longitude or 0.0,
        installed_peak_power_kw=record.installed_peak_power_kw or 0.0,
        azimuth_deg=record.azimuth_deg,
        tilt_deg=record.tilt_deg,
        inverter_max_power_kw=record.inverter_max_power_kw,
        system_loss_percent=record.system_loss_percent,
        enabled=record.enabled,
        tilt_estimated=record.tilt_estimated,
        azimuth_estimated=record.azimuth_estimated,
        timezone=record.timezone,
        solar_intelligence_enabled=getattr(record, "solar_intelligence_enabled", False),
    )


class SolarSiteConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, site_id: int, *, timezone: str = "UTC") -> SolarConfigRecord | None:
        row = await self._session.get(SolarSiteConfigurationModel, site_id)
        if row is None:
            return None
        return SolarConfigRecord(
            site_id=row.site_id,
            latitude=row.latitude,
            longitude=row.longitude,
            installed_peak_power_kw=row.installed_peak_power_kw,
            azimuth_deg=row.azimuth_deg,
            tilt_deg=row.tilt_deg,
            inverter_max_power_kw=row.inverter_max_power_kw,
            system_loss_percent=row.system_loss_percent,
            enabled=row.enabled,
            tilt_estimated=row.tilt_estimated,
            azimuth_estimated=row.azimuth_estimated,
            timezone=timezone,
            solar_intelligence_enabled=getattr(row, "solar_intelligence_enabled", False),
        )

    async def upsert(
        self,
        site_id: int,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        installed_peak_power_kw: float | None = None,
        azimuth_deg: float | None = None,
        tilt_deg: float | None = None,
        inverter_max_power_kw: float | None = None,
        system_loss_percent: float | None = None,
        enabled: bool | None = None,
        tilt_estimated: bool | None = None,
        azimuth_estimated: bool | None = None,
        solar_intelligence_enabled: bool | None = None,
    ) -> SolarSiteConfigurationModel:
        row = await self._session.get(SolarSiteConfigurationModel, site_id)
        now = datetime.now(UTC)
        if row is None:
            row = SolarSiteConfigurationModel(site_id=site_id)
            self._session.add(row)
        if latitude is not None:
            row.latitude = latitude
        if longitude is not None:
            row.longitude = longitude
        if installed_peak_power_kw is not None:
            row.installed_peak_power_kw = installed_peak_power_kw
        if azimuth_deg is not None:
            row.azimuth_deg = azimuth_deg
        if tilt_deg is not None:
            row.tilt_deg = tilt_deg
        if inverter_max_power_kw is not None:
            row.inverter_max_power_kw = inverter_max_power_kw
        if system_loss_percent is not None:
            row.system_loss_percent = system_loss_percent
        if enabled is not None:
            row.enabled = enabled
        if tilt_estimated is not None:
            row.tilt_estimated = tilt_estimated
        if azimuth_estimated is not None:
            row.azimuth_estimated = azimuth_estimated
        if solar_intelligence_enabled is not None:
            row.solar_intelligence_enabled = solar_intelligence_enabled
        row.config_updated_at = now
        await self._session.flush()
        return row

    async def bump_configuration_version(
        self,
        site_id: int,
        snapshot: dict,
        *,
        significant_change: bool,
    ) -> int:
        """Return current configuration version; bump if significant fields changed."""
        stmt = (
            select(SolarSiteConfigurationVersionModel)
            .where(SolarSiteConfigurationVersionModel.site_id == site_id)
            .order_by(desc(SolarSiteConfigurationVersionModel.version))
            .limit(1)
        )
        latest = await self._session.scalar(stmt)
        current_version = latest.version if latest else 0
        if not significant_change:
            return current_version or 1
        new_version = (current_version or 0) + 1
        self._session.add(
            SolarSiteConfigurationVersionModel(
                site_id=site_id,
                version=new_version,
                effective_from=datetime.now(UTC),
                config_snapshot_json=json.dumps(snapshot),
            )
        )
        await self._session.flush()
        return new_version

    async def get_configuration_version(self, site_id: int) -> int:
        stmt = (
            select(SolarSiteConfigurationVersionModel.version)
            .where(SolarSiteConfigurationVersionModel.site_id == site_id)
            .order_by(desc(SolarSiteConfigurationVersionModel.version))
            .limit(1)
        )
        version = await self._session.scalar(stmt)
        return version or 1

    async def touch_forecast(self, site_id: int) -> None:
        row = await self._session.get(SolarSiteConfigurationModel, site_id)
        if row:
            row.last_forecast_at = datetime.now(UTC)


class SolarWeatherCacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_valid(self, site_id: int, *, now: datetime | None = None) -> WeatherForecast | None:
        now = now or datetime.now(UTC)
        stmt = (
            select(SolarWeatherCacheModel)
            .where(SolarWeatherCacheModel.site_id == site_id)
            .where(SolarWeatherCacheModel.valid_until >= now)
            .order_by(desc(SolarWeatherCacheModel.fetched_at))
            .limit(1)
        )
        row = await self._session.scalar(stmt)
        if row is None:
            return None
        return _weather_from_json(site_id, row.payload_json, row.fetched_at, row.provider, source="cache")

    async def save(self, weather: WeatherForecast, *, valid_until: datetime) -> None:
        payload = _weather_to_json(weather)
        self._session.add(
            SolarWeatherCacheModel(
                site_id=weather.site_id,
                fetched_at=weather.fetched_at,
                provider=weather.provider,
                payload_json=payload,
                valid_until=valid_until,
            )
        )

    async def prune_old(self, site_id: int, *, keep_after: datetime) -> None:
        await self._session.execute(
            delete(SolarWeatherCacheModel).where(
                SolarWeatherCacheModel.site_id == site_id,
                SolarWeatherCacheModel.fetched_at < keep_after,
            )
        )


class SolarForecastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_run(self, forecast: SolarForecast) -> int:
        run = SolarForecastRunModel(
            site_id=forecast.site_id,
            generated_at=forecast.generated_at,
            model_version=forecast.model_version,
            quality=forecast.quality,
            weather_source=forecast.weather_source,
            confidence=forecast.confidence,
            expected_today_kwh=forecast.expected_today_kwh,
            remaining_today_kwh=forecast.remaining_today_kwh,
            expected_tomorrow_kwh=forecast.expected_tomorrow_kwh,
            peak_power_w=forecast.peak_power_w,
            peak_time=forecast.peak_time,
            lower_today_kwh=forecast.lower_today_kwh,
            upper_today_kwh=forecast.upper_today_kwh,
            weather_summary=forecast.weather_summary,
        )
        self._session.add(run)
        await self._session.flush()
        for p in forecast.points:
            self._session.add(
                SolarForecastPointModel(
                    run_id=run.id,
                    timestamp=p.timestamp,
                    baseline_power_w=p.baseline_power_w,
                    corrected_power_w=p.corrected_power_w,
                    expected_energy_kwh=p.expected_energy_kwh,
                    lower_bound_power_w=p.lower_bound_power_w,
                    upper_bound_power_w=p.upper_bound_power_w,
                    confidence=p.confidence,
                    correction_factor=p.correction_factor,
                    gti_wm2=p.gti_wm2,
                    cloud_cover_pct=p.cloud_cover_pct,
                )
            )
        return run.id

    async def get_latest(self, site_id: int) -> SolarForecast | None:
        stmt = (
            select(SolarForecastRunModel)
            .where(SolarForecastRunModel.site_id == site_id)
            .order_by(desc(SolarForecastRunModel.generated_at))
            .limit(1)
        )
        run = await self._session.scalar(stmt)
        if run is None:
            return None
        pts = await self._session.scalars(
            select(SolarForecastPointModel)
            .where(SolarForecastPointModel.run_id == run.id)
            .order_by(SolarForecastPointModel.timestamp)
        )
        return _forecast_from_models(run, list(pts))

    async def prune_runs(self, site_id: int, *, keep_after: datetime) -> None:
        old_runs = await self._session.scalars(
            select(SolarForecastRunModel.id).where(
                SolarForecastRunModel.site_id == site_id,
                SolarForecastRunModel.generated_at < keep_after,
            )
        )
        for run_id in old_runs:
            await self._session.execute(delete(SolarForecastPointModel).where(SolarForecastPointModel.run_id == run_id))
            await self._session.execute(delete(SolarForecastRunModel).where(SolarForecastRunModel.id == run_id))


class SolarPerformanceProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, site_id: int) -> SitePerformanceProfile:
        row = await self._session.get(SolarSitePerformanceProfileModel, site_id)
        if row is None:
            return SitePerformanceProfile(site_id=site_id)
        return SitePerformanceProfile(
            site_id=site_id,
            global_factor=row.global_factor,
            seasonal_factors=json.loads(row.seasonal_factors_json),
            hour_factors={int(k): v for k, v in json.loads(row.hour_factors_json).items()},
            weather_factors=json.loads(row.weather_factors_json),
            sample_count=row.sample_count,
            mape_7d=row.mape_7d,
            mape_30d=row.mape_30d,
            mae_kwh_30d=row.mae_kwh_30d,
            bias_pct_30d=row.bias_pct_30d,
            updated_at=row.updated_at,
        )

    async def save(self, profile: SitePerformanceProfile) -> None:
        row = await self._session.get(SolarSitePerformanceProfileModel, profile.site_id)
        if row is None:
            row = SolarSitePerformanceProfileModel(site_id=profile.site_id)
            self._session.add(row)
        row.global_factor = profile.global_factor
        row.seasonal_factors_json = json.dumps({str(k): v for k, v in profile.seasonal_factors.items()})
        row.hour_factors_json = json.dumps({str(k): v for k, v in profile.hour_factors.items()})
        row.weather_factors_json = json.dumps(profile.weather_factors)
        row.sample_count = profile.sample_count
        row.mape_7d = profile.mape_7d
        row.mape_30d = profile.mape_30d
        row.mae_kwh_30d = profile.mae_kwh_30d
        row.bias_pct_30d = profile.bias_pct_30d
        row.updated_at = profile.updated_at or datetime.now(UTC)


class SolarEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, evaluation: ForecastEvaluation) -> None:
        existing = await self._session.get(
            SolarForecastEvaluationModel,
            (evaluation.site_id, evaluation.bucket_start),
        )
        if existing is None:
            self._session.add(
                SolarForecastEvaluationModel(
                    site_id=evaluation.site_id,
                    bucket_start=evaluation.bucket_start,
                    forecasted_energy_kwh=evaluation.forecasted_energy_kwh,
                    actual_energy_kwh=evaluation.actual_energy_kwh,
                    absolute_error_kwh=evaluation.absolute_error_kwh,
                    percentage_error=evaluation.percentage_error,
                    squared_error=evaluation.squared_error,
                    model_version=evaluation.model_version,
                )
            )
        else:
            existing.forecasted_energy_kwh = evaluation.forecasted_energy_kwh
            existing.actual_energy_kwh = evaluation.actual_energy_kwh
            existing.absolute_error_kwh = evaluation.absolute_error_kwh
            existing.percentage_error = evaluation.percentage_error
            existing.squared_error = evaluation.squared_error
            existing.model_version = evaluation.model_version

    async def list_since(self, site_id: int, since: datetime) -> list[ForecastEvaluation]:
        rows = await self._session.scalars(
            select(SolarForecastEvaluationModel)
            .where(
                SolarForecastEvaluationModel.site_id == site_id,
                SolarForecastEvaluationModel.bucket_start >= since,
            )
            .order_by(SolarForecastEvaluationModel.bucket_start)
        )
        return [
            ForecastEvaluation(
                site_id=r.site_id,
                forecast_timestamp=r.bucket_start,
                bucket_start=r.bucket_start,
                forecasted_energy_kwh=r.forecasted_energy_kwh,
                actual_energy_kwh=r.actual_energy_kwh,
                absolute_error_kwh=r.absolute_error_kwh,
                percentage_error=r.percentage_error,
                squared_error=r.squared_error,
                model_version=r.model_version,
            )
            for r in rows
        ]


def _weather_to_json(weather: WeatherForecast) -> str:
    points = [
        {
            "timestamp": p.timestamp.isoformat(),
            "ghi_wm2": p.ghi_wm2,
            "direct_radiation_wm2": p.direct_radiation_wm2,
            "diffuse_radiation_wm2": p.diffuse_radiation_wm2,
            "gti_wm2": p.gti_wm2,
            "cloud_cover_pct": p.cloud_cover_pct,
            "temperature_c": p.temperature_c,
            "precipitation_mm": p.precipitation_mm,
            "weather_code": p.weather_code,
            "sunshine_duration_s": p.sunshine_duration_s,
        }
        for p in weather.points
    ]
    return json.dumps({"provider": weather.provider, "points": points})


def _weather_from_json(
    site_id: int,
    payload: str,
    fetched_at: datetime,
    provider: str,
    *,
    source: str,
) -> WeatherForecast:
    data = json.loads(payload)
    points = []
    for p in data.get("points", []):
        ts = datetime.fromisoformat(p["timestamp"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        points.append(
            WeatherForecastPoint(
                timestamp=ts,
                ghi_wm2=p.get("ghi_wm2"),
                direct_radiation_wm2=p.get("direct_radiation_wm2"),
                diffuse_radiation_wm2=p.get("diffuse_radiation_wm2"),
                gti_wm2=p.get("gti_wm2"),
                cloud_cover_pct=p.get("cloud_cover_pct"),
                temperature_c=p.get("temperature_c"),
                precipitation_mm=p.get("precipitation_mm"),
                weather_code=p.get("weather_code"),
                sunshine_duration_s=p.get("sunshine_duration_s"),
            )
        )
    return WeatherForecast(
        site_id=site_id,
        fetched_at=fetched_at,
        provider=provider,
        points=tuple(points),
        source=source,  # type: ignore[arg-type]
    )


def _forecast_from_models(run: SolarForecastRunModel, points: list[SolarForecastPointModel]) -> SolarForecast:
    from energy_core.solar_forecast.physical import baseline_energy_kwh

    today_pts = points
    raw_today = sum(baseline_energy_kwh(p.baseline_power_w) for p in today_pts)
    return SolarForecast(
        site_id=run.site_id,
        generated_at=run.generated_at,
        model_version=run.model_version,
        quality=run.quality,  # type: ignore[arg-type]
        weather_source=run.weather_source,  # type: ignore[arg-type]
        expected_today_kwh=run.expected_today_kwh,
        remaining_today_kwh=run.remaining_today_kwh,
        expected_tomorrow_kwh=run.expected_tomorrow_kwh,
        peak_power_w=run.peak_power_w,
        peak_time=run.peak_time,
        confidence=run.confidence,
        lower_today_kwh=run.lower_today_kwh,
        upper_today_kwh=run.upper_today_kwh,
        weather_summary=run.weather_summary,
        raw_forecast_today_kwh=raw_today,
        corrected_forecast_today_kwh=run.expected_today_kwh,
        corrected_forecast_tomorrow_kwh=run.expected_tomorrow_kwh,
        points=tuple(
            SolarForecastPoint(
                timestamp=p.timestamp,
                baseline_power_w=p.baseline_power_w,
                corrected_power_w=p.corrected_power_w,
                expected_energy_kwh=p.expected_energy_kwh,
                lower_bound_power_w=p.lower_bound_power_w,
                upper_bound_power_w=p.upper_bound_power_w,
                confidence=p.confidence,
                gti_wm2=p.gti_wm2,
                cloud_cover_pct=p.cloud_cover_pct,
                correction_factor=p.correction_factor,
            )
            for p in points
        ),
    )


def _observation_to_domain(row: SolarForecastObservationModel) -> SolarForecastObservation:
    hourly = json.loads(row.cloud_cover_hourly_json) if row.cloud_cover_hourly_json else None
    return SolarForecastObservation(
        site_id=row.site_id,
        forecast_date=row.forecast_date,
        forecast_generated_at=row.forecast_generated_at,
        forecast_kwh_raw=row.forecast_kwh_raw,
        forecast_kwh_corrected=row.forecast_kwh_corrected,
        actual_kwh=row.actual_kwh,
        weather_provider=row.weather_provider,
        weather_model=row.weather_model,
        cloud_cover_avg=row.cloud_cover_avg,
        cloud_cover_hourly=hourly,
        solar_radiation=row.solar_radiation,
        temperature_avg=row.temperature_avg,
        precipitation=row.precipitation,
        sunshine_duration=row.sunshine_duration,
        sunrise=row.sunrise,
        sunset=row.sunset,
        weather_condition_bucket=row.weather_condition_bucket,
        correction_factor_used=row.correction_factor_used,
        absolute_error_kwh=row.absolute_error_kwh,
        percentage_error=row.percentage_error,
        signed_error_kwh=row.signed_error_kwh,
        raw_absolute_error_kwh=row.raw_absolute_error_kwh,
        raw_percentage_error=row.raw_percentage_error,
        data_completeness_pct=row.data_completeness_pct,
        training_eligible=row.training_eligible,
        exclusion_reason=row.exclusion_reason,
        physical_kwh=getattr(row, "physical_kwh", None),
        learned_correction_pct=getattr(row, "learned_correction_pct", None),
        radiation_kwh_m2=getattr(row, "radiation_kwh_m2", None),
        provenance=getattr(row, "provenance", None),
        model_version=row.model_version,
        site_configuration_version=row.site_configuration_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SolarForecastObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, observation: SolarForecastObservation) -> None:
        row = await self._session.get(
            SolarForecastObservationModel,
            (observation.site_id, observation.forecast_date),
        )
        hourly_json = json.dumps(observation.cloud_cover_hourly) if observation.cloud_cover_hourly else None
        now = datetime.now(UTC)
        if row is None:
            self._session.add(
                SolarForecastObservationModel(
                    site_id=observation.site_id,
                    forecast_date=observation.forecast_date,
                    forecast_generated_at=observation.forecast_generated_at,
                    forecast_kwh_raw=observation.forecast_kwh_raw,
                    forecast_kwh_corrected=observation.forecast_kwh_corrected,
                    actual_kwh=observation.actual_kwh,
                    weather_provider=observation.weather_provider,
                    weather_model=observation.weather_model,
                    cloud_cover_avg=observation.cloud_cover_avg,
                    cloud_cover_hourly_json=hourly_json,
                    solar_radiation=observation.solar_radiation,
                    temperature_avg=observation.temperature_avg,
                    precipitation=observation.precipitation,
                    sunshine_duration=observation.sunshine_duration,
                    sunrise=observation.sunrise,
                    sunset=observation.sunset,
                    weather_condition_bucket=observation.weather_condition_bucket,
                    correction_factor_used=observation.correction_factor_used,
                    absolute_error_kwh=observation.absolute_error_kwh,
                    percentage_error=observation.percentage_error,
                    signed_error_kwh=observation.signed_error_kwh,
                    raw_absolute_error_kwh=observation.raw_absolute_error_kwh,
                    raw_percentage_error=observation.raw_percentage_error,
                    data_completeness_pct=observation.data_completeness_pct,
                    training_eligible=observation.training_eligible,
                    exclusion_reason=observation.exclusion_reason,
                    physical_kwh=observation.physical_kwh,
                    learned_correction_pct=observation.learned_correction_pct,
                    radiation_kwh_m2=observation.radiation_kwh_m2,
                    provenance=observation.provenance,
                    model_version=observation.model_version,
                    site_configuration_version=observation.site_configuration_version,
                    created_at=observation.created_at or now,
                    updated_at=now,
                )
            )
        else:
            if observation.forecast_generated_at is not None:
                row.forecast_generated_at = observation.forecast_generated_at
            if observation.forecast_kwh_raw is not None:
                row.forecast_kwh_raw = observation.forecast_kwh_raw
            if observation.forecast_kwh_corrected is not None:
                row.forecast_kwh_corrected = observation.forecast_kwh_corrected
            if observation.actual_kwh is not None:
                row.actual_kwh = observation.actual_kwh
            row.weather_provider = observation.weather_provider or row.weather_provider
            row.weather_model = observation.weather_model or row.weather_model
            row.cloud_cover_avg = observation.cloud_cover_avg
            row.cloud_cover_hourly_json = hourly_json
            row.solar_radiation = observation.solar_radiation
            row.weather_condition_bucket = observation.weather_condition_bucket
            row.correction_factor_used = observation.correction_factor_used
            row.absolute_error_kwh = observation.absolute_error_kwh
            row.percentage_error = observation.percentage_error
            row.signed_error_kwh = observation.signed_error_kwh
            row.raw_absolute_error_kwh = observation.raw_absolute_error_kwh
            row.raw_percentage_error = observation.raw_percentage_error
            row.data_completeness_pct = observation.data_completeness_pct
            row.training_eligible = observation.training_eligible
            row.exclusion_reason = observation.exclusion_reason
            if observation.physical_kwh is not None:
                row.physical_kwh = observation.physical_kwh
            if observation.radiation_kwh_m2 is not None:
                row.radiation_kwh_m2 = observation.radiation_kwh_m2
            if observation.provenance is not None:
                row.provenance = observation.provenance
            row.model_version = observation.model_version
            row.site_configuration_version = observation.site_configuration_version
            row.updated_at = now

    async def get(self, site_id: int, forecast_date: date) -> SolarForecastObservation | None:
        row = await self._session.get(SolarForecastObservationModel, (site_id, forecast_date))
        return _observation_to_domain(row) if row else None

    async def list_for_site(
        self,
        site_id: int,
        *,
        since: date | None = None,
        limit: int = 90,
    ) -> list[SolarForecastObservation]:
        stmt = (
            select(SolarForecastObservationModel)
            .where(SolarForecastObservationModel.site_id == site_id)
            .order_by(desc(SolarForecastObservationModel.forecast_date))
            .limit(limit)
        )
        if since is not None:
            stmt = stmt.where(SolarForecastObservationModel.forecast_date >= since)
        rows = await self._session.scalars(stmt)
        return [_observation_to_domain(r) for r in rows]

    async def list_training_eligible(self, site_id: int, *, days: int = 90) -> list[SolarForecastObservation]:
        since = datetime.now(UTC).date().fromordinal(datetime.now(UTC).date().toordinal() - days)
        stmt = (
            select(SolarForecastObservationModel)
            .where(
                SolarForecastObservationModel.site_id == site_id,
                SolarForecastObservationModel.forecast_date >= since,
                SolarForecastObservationModel.training_eligible.is_(True),
                SolarForecastObservationModel.actual_kwh.is_not(None),
            )
            .order_by(SolarForecastObservationModel.forecast_date)
        )
        rows = await self._session.scalars(stmt)
        return [_observation_to_domain(r) for r in rows]


def _model_profile_to_domain(row: SolarForecastModelProfileModel) -> SolarForecastModelProfile:
    return SolarForecastModelProfile(
        site_id=row.site_id,
        model_version=row.model_version,
        historical_samples=row.historical_samples,
        model_state=ModelState(row.model_state),
        mape_7d=row.mape_7d,
        mape_30d=row.mape_30d,
        mape_90d=row.mape_90d,
        mape_7d_valid_days=row.mape_7d_valid_days,
        mape_30d_valid_days=row.mape_30d_valid_days,
        mape_90d_valid_days=row.mape_90d_valid_days,
        mae_7d=row.mae_7d,
        mae_30d=row.mae_30d,
        mae_90d=row.mae_90d,
        bias_7d=row.bias_7d,
        bias_30d=row.bias_30d,
        bias_90d=row.bias_90d,
        wape_7d=getattr(row, "wape_7d", None),
        wape_30d=getattr(row, "wape_30d", None),
        wape_90d=getattr(row, "wape_90d", None),
        rmse_7d=getattr(row, "rmse_7d", None),
        rmse_30d=getattr(row, "rmse_30d", None),
        rmse_90d=getattr(row, "rmse_90d", None),
        r2_7d=getattr(row, "r2_7d", None),
        r2_30d=getattr(row, "r2_30d", None),
        r2_90d=getattr(row, "r2_90d", None),
        raw_mae_30d=row.raw_mae_30d,
        corrected_mae_30d=row.corrected_mae_30d,
        improvement_pct_30d=row.improvement_pct_30d,
        correction_factor=row.correction_factor,
        confidence_score=row.confidence_score,
        seasonal_factors={int(k): v for k, v in json.loads(row.seasonal_factors_json).items()},
        last_training_at=row.last_training_at,
        last_evaluation_at=row.last_evaluation_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SolarForecastModelProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, site_id: int) -> SolarForecastModelProfile:
        row = await self._session.get(SolarForecastModelProfileModel, site_id)
        if row is None:
            return SolarForecastModelProfile(site_id=site_id)
        return _model_profile_to_domain(row)

    async def save(self, profile: SolarForecastModelProfile) -> None:
        row = await self._session.get(SolarForecastModelProfileModel, profile.site_id)
        now = datetime.now(UTC)
        if row is None:
            row = SolarForecastModelProfileModel(site_id=profile.site_id)
            self._session.add(row)
            row.created_at = profile.created_at or now
        row.model_version = profile.model_version
        row.historical_samples = profile.historical_samples
        row.model_state = profile.model_state.value
        row.mape_7d = profile.mape_7d
        row.mape_30d = profile.mape_30d
        row.mape_90d = profile.mape_90d
        row.mape_7d_valid_days = profile.mape_7d_valid_days
        row.mape_30d_valid_days = profile.mape_30d_valid_days
        row.mape_90d_valid_days = profile.mape_90d_valid_days
        row.mae_7d = profile.mae_7d
        row.mae_30d = profile.mae_30d
        row.mae_90d = profile.mae_90d
        row.bias_7d = profile.bias_7d
        row.bias_30d = profile.bias_30d
        row.bias_90d = profile.bias_90d
        row.wape_7d = profile.wape_7d
        row.wape_30d = profile.wape_30d
        row.wape_90d = profile.wape_90d
        row.rmse_7d = profile.rmse_7d
        row.rmse_30d = profile.rmse_30d
        row.rmse_90d = profile.rmse_90d
        row.r2_7d = profile.r2_7d
        row.r2_30d = profile.r2_30d
        row.r2_90d = profile.r2_90d
        row.raw_mae_30d = profile.raw_mae_30d
        row.corrected_mae_30d = profile.corrected_mae_30d
        row.improvement_pct_30d = profile.improvement_pct_30d
        row.correction_factor = profile.correction_factor
        row.confidence_score = profile.confidence_score
        row.seasonal_factors_json = json.dumps({str(k): v for k, v in profile.seasonal_factors.items()})
        row.last_training_at = profile.last_training_at
        row.last_evaluation_at = profile.last_evaluation_at
        row.updated_at = profile.updated_at or now


class SolarArrayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_default_for_site(self, site_id: int, config: SolarSiteConfiguration) -> None:
        stmt = select(SolarArrayModel).where(SolarArrayModel.site_id == site_id).limit(1)
        existing = await self._session.scalar(stmt)
        if existing is not None:
            return
        self._session.add(
            SolarArrayModel(
                site_id=site_id,
                name="Main",
                capacity_kwp=config.installed_peak_power_kw,
                azimuth_degrees=config.azimuth_deg or 180.0,
                tilt_degrees=config.tilt_deg or 35.0,
            )
        )
        await self._session.flush()
