"""Daily forecast snapshot archive (Phase 0)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.daily_evaluation import forecast_kwh_for_day
from energy_core.solar_forecast.types import MODEL_VERSION, SolarForecast


def snapshot_from_forecast(
    site_id: int,
    day: date,
    forecast: SolarForecast,
    *,
    timezone: str,
    run_id: int | None = None,
) -> dict:
    raw_kwh, corrected_kwh = forecast_kwh_for_day(forecast, day, timezone)
    return {
        "site_id": site_id,
        "forecast_date": day,
        "snapshot_at": datetime.now(UTC),
        "forecast_kwh_raw": raw_kwh,
        "forecast_kwh_corrected": corrected_kwh,
        "run_id": run_id,
        "model_version": MODEL_VERSION,
        "weather_source": forecast.weather_source,
        "created_at": datetime.now(UTC),
    }


def local_today(timezone: str, *, now: datetime | None = None) -> date:
    now = now or datetime.now(UTC)
    return now.astimezone(ZoneInfo(timezone)).date()
