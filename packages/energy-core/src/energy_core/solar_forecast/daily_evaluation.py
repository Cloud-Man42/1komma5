"""Daily solar forecast observation evaluation."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from energy_core.config import Settings, get_settings
from energy_core.solar_forecast.calibration import (
    build_model_profile,
    is_outlier_ratio,
    weather_condition_bucket,
)
from energy_core.solar_forecast.historical import aggregate_buckets_from_readings, actual_energy_kwh
from energy_core.solar_forecast.physical import baseline_energy_kwh, baseline_power_w
from energy_core.solar_forecast.types import (
    MODEL_VERSION,
    SolarForecast,
    SolarForecastObservation,
    SolarForecastModelProfile,
    SolarSiteConfiguration,
    WeatherForecastPoint,
)

logger = logging.getLogger(__name__)


def local_day_bounds(day: date, timezone: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone)
    start = datetime.combine(day, time.min, tzinfo=tz).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    return start, end


def actual_kwh_for_day(
    readings: list[tuple[datetime, float, float]],
    day: date,
    timezone: str,
) -> tuple[float, float]:
    """Return (actual_kwh, data_completeness_pct) for a local calendar day."""
    day_start, day_end = local_day_bounds(day, timezone)
    day_readings = [
        (ts, solar_w, consumption_w)
        for ts, solar_w, consumption_w in readings
        if day_start <= (ts if ts.tzinfo else ts.replace(tzinfo=UTC)) < day_end
    ]
    if not day_readings:
        return 0.0, 0.0

    buckets = aggregate_buckets_from_readings(day_readings)
    actual = sum(actual_energy_kwh(b.avg_solar_w) for b in buckets)
    if not buckets:
        return 0.0, 0.0
    completeness = sum(min(1.0, b.sample_count / max(1, b.expected_samples)) for b in buckets) / len(buckets) * 100.0
    return round(actual, 3), round(completeness, 1)


def forecast_kwh_for_day(forecast: SolarForecast, day: date, timezone: str) -> tuple[float, float]:
    """Sum raw (baseline) and corrected forecast kWh for a local day from run points."""
    tz = ZoneInfo(timezone)
    raw = 0.0
    corrected = 0.0
    for p in forecast.points:
        if p.timestamp.astimezone(tz).date() != day:
            continue
        raw += baseline_energy_kwh(p.baseline_power_w)
        corrected += p.expected_energy_kwh
    return round(raw, 3), round(corrected, 3)


def weather_snapshot_for_day(
    forecast: SolarForecast,
    day: date,
    timezone: str,
) -> dict:
    tz = ZoneInfo(timezone)
    day_points = [p for p in forecast.points if p.timestamp.astimezone(tz).date() == day]
    if not day_points:
        return {}
    clouds = [p.cloud_cover_pct for p in day_points if p.cloud_cover_pct is not None]
    gtis = [p.gti_wm2 for p in day_points if p.gti_wm2 is not None]
    cloud_avg = sum(clouds) / len(clouds) if clouds else None
    return {
        "cloud_cover_avg": cloud_avg,
        "cloud_cover_hourly": clouds[:24] if clouds else None,
        "solar_radiation": sum(gtis) / len(gtis) if gtis else None,
        "weather_condition_bucket": weather_condition_bucket(cloud_avg),
    }


def evaluate_observation_errors(
    *,
    actual_kwh: float,
    raw_kwh: float,
    corrected_kwh: float,
) -> dict[str, float | None]:
    raw_err = abs(actual_kwh - raw_kwh)
    corr_err = abs(actual_kwh - corrected_kwh)
    signed = corrected_kwh - actual_kwh
    pct = (corr_err / actual_kwh * 100.0) if actual_kwh > 0.01 else None
    raw_pct = (raw_err / actual_kwh * 100.0) if actual_kwh > 0.01 else None
    return {
        "absolute_error_kwh": round(corr_err, 3),
        "percentage_error": round(pct, 2) if pct is not None else None,
        "signed_error_kwh": round(signed, 3),
        "raw_absolute_error_kwh": round(raw_err, 3),
        "raw_percentage_error": round(raw_pct, 2) if raw_pct is not None else None,
    }


def determine_training_eligibility(
    *,
    actual_kwh: float | None,
    data_completeness_pct: float,
    raw_kwh: float | None,
    settings: Settings | None = None,
) -> tuple[bool, str | None]:
    cfg = settings or get_settings()
    if actual_kwh is None:
        return False, "actual_missing"
    if data_completeness_pct < cfg.solar_forecast_min_data_completeness_pct:
        return False, "incomplete_data"
    if raw_kwh is not None and raw_kwh > 0:
        ratio = actual_kwh / raw_kwh
        if is_outlier_ratio(ratio, cfg):
            return False, "outlier_ratio"
    return True, None


def build_observation_from_day(
    site_id: int,
    day: date,
    *,
    forecast: SolarForecast | None,
    actual_kwh: float,
    data_completeness_pct: float,
    timezone: str,
    correction_factor_used: float = 1.0,
    site_configuration_version: int = 1,
    settings: Settings | None = None,
) -> SolarForecastObservation:
    cfg = settings or get_settings()
    now = datetime.now(UTC)
    raw_kwh: float | None = None
    corrected_kwh: float | None = None
    generated_at: datetime | None = None
    weather_meta: dict = {}

    if forecast is not None:
        raw_kwh, corrected_kwh = forecast_kwh_for_day(forecast, day, timezone)
        generated_at = forecast.generated_at
        weather_meta = weather_snapshot_for_day(forecast, day, timezone)

    eligible, reason = determine_training_eligibility(
        actual_kwh=actual_kwh,
        data_completeness_pct=data_completeness_pct,
        raw_kwh=raw_kwh,
        settings=cfg,
    )
    errors = evaluate_observation_errors(
        actual_kwh=actual_kwh,
        raw_kwh=raw_kwh or 0.0,
        corrected_kwh=corrected_kwh or 0.0,
    )

    return SolarForecastObservation(
        site_id=site_id,
        forecast_date=day,
        forecast_generated_at=generated_at,
        forecast_kwh_raw=raw_kwh,
        forecast_kwh_corrected=corrected_kwh,
        actual_kwh=actual_kwh,
        weather_provider=forecast.weather_source if forecast else None,
        weather_model=MODEL_VERSION if forecast else None,
        cloud_cover_avg=weather_meta.get("cloud_cover_avg"),
        cloud_cover_hourly=weather_meta.get("cloud_cover_hourly"),
        solar_radiation=weather_meta.get("solar_radiation"),
        weather_condition_bucket=weather_meta.get("weather_condition_bucket"),
        correction_factor_used=correction_factor_used,
        absolute_error_kwh=errors["absolute_error_kwh"],
        percentage_error=errors["percentage_error"],
        signed_error_kwh=errors["signed_error_kwh"],
        raw_absolute_error_kwh=errors["raw_absolute_error_kwh"],
        raw_percentage_error=errors["raw_percentage_error"],
        data_completeness_pct=data_completeness_pct,
        training_eligible=eligible,
        exclusion_reason=reason,
        model_version=MODEL_VERSION,
        site_configuration_version=site_configuration_version,
        created_at=now,
        updated_at=now,
    )


def build_forecast_observation_stub(
    site_id: int,
    day: date,
    *,
    forecast: SolarForecast,
    timezone: str,
    correction_factor_used: float,
    site_configuration_version: int = 1,
) -> SolarForecastObservation:
    """Create/update observation row when forecast is generated (actual may be null)."""
    raw_kwh, corrected_kwh = forecast_kwh_for_day(forecast, day, timezone)
    weather_meta = weather_snapshot_for_day(forecast, day, timezone)
    now = datetime.now(UTC)
    return SolarForecastObservation(
        site_id=site_id,
        forecast_date=day,
        forecast_generated_at=forecast.generated_at,
        forecast_kwh_raw=raw_kwh,
        forecast_kwh_corrected=corrected_kwh,
        actual_kwh=None,
        weather_provider=forecast.weather_source,
        weather_model=MODEL_VERSION,
        cloud_cover_avg=weather_meta.get("cloud_cover_avg"),
        cloud_cover_hourly=weather_meta.get("cloud_cover_hourly"),
        solar_radiation=weather_meta.get("solar_radiation"),
        weather_condition_bucket=weather_meta.get("weather_condition_bucket"),
        correction_factor_used=correction_factor_used,
        training_eligible=False,
        exclusion_reason="day_not_complete",
        model_version=MODEL_VERSION,
        site_configuration_version=site_configuration_version,
        created_at=now,
        updated_at=now,
    )


def recompute_profile_from_observations(
    site_id: int,
    observations: list[SolarForecastObservation],
    *,
    previous: SolarForecastModelProfile | None = None,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> SolarForecastModelProfile:
    return build_model_profile(
        site_id,
        observations,
        previous=previous,
        now=now,
        settings=settings,
    )


def days_to_evaluate(
    timezone: str,
    now: datetime | None = None,
    *,
    include_today_if_complete: bool = False,
) -> list[date]:
    """Return local calendar days that may need daily evaluation (typically yesterday)."""
    now = now or datetime.now(UTC)
    tz = ZoneInfo(timezone)
    local_now = now.astimezone(tz)
    days = [local_now.date() - timedelta(days=1)]
    if include_today_if_complete and local_now.hour >= 23:
        days.append(local_now.date())
    return days
