"""Build persisted solar forecast API response payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.config import Settings
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.db.solar_forecast_repo import SolarForecastModelProfileRepository
from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics, compute_tomorrow_kwh
from energy_core.solar_forecast.rollup_queries import actual_solar_kwh_today, count_production_days_observed
from energy_core.solar_forecast.types import ModelState, confidence_label_from_score
from sqlalchemy.ext.asyncio import AsyncSession


async def build_solar_forecast_api_payload(
    session: AsyncSession,
    site,
    forecast,
    settings: Settings,
) -> dict[str, Any]:
    """Build a JSON-serializable payload matching SolarForecastResponse."""
    now = datetime.now(UTC)
    day_metrics = compute_solar_day_metrics(forecast, timezone=site.timezone, now=now)
    expected_tomorrow_kwh = compute_tomorrow_kwh(forecast, timezone=site.timezone, now=now)

    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    actual_today_kwh = await actual_solar_kwh_today(
        reading_repo,
        site.id,
        timezone=site.timezone,
        now=now,
    )
    remaining_vs_expected_kwh = round(
        max(0.0, day_metrics.expected_today_kwh - actual_today_kwh),
        3,
    )

    model_profile_repo = SolarForecastModelProfileRepository(session)
    model_profile = await model_profile_repo.get(site.id)
    production_days = await count_production_days_observed(
        reading_repo,
        site.id,
        timezone=site.timezone,
        window_days=settings.solar_forecast_rolling_window_days,
        now=now,
    )

    conf_score = getattr(forecast, "confidence_score", None) or model_profile.confidence_score
    conf_label = confidence_label_from_score(conf_score)
    model_state = getattr(forecast, "model_state", model_profile.model_state)
    if isinstance(model_state, ModelState):
        model_state = model_state.value

    generated_at = forecast.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=UTC)

    return {
        "site_id": forecast.site_id,
        "generated_at": generated_at.isoformat(),
        "model_version": forecast.model_version,
        "quality": forecast.quality,
        "weather_source": forecast.weather_source,
        "expected_today_kwh": day_metrics.expected_today_kwh,
        "remaining_today_kwh": day_metrics.remaining_today_kwh,
        "expected_tomorrow_kwh": expected_tomorrow_kwh,
        "peak_power_w": day_metrics.peak_power_w,
        "peak_time": day_metrics.peak_time.isoformat() if day_metrics.peak_time else None,
        "confidence": forecast.confidence,
        "lower_today_kwh": forecast.lower_today_kwh,
        "upper_today_kwh": forecast.upper_today_kwh,
        "weather_summary": forecast.weather_summary,
        "actual_today_kwh": actual_today_kwh,
        "forecast_so_far_kwh": day_metrics.forecast_so_far_kwh,
        "remaining_vs_expected_kwh": remaining_vs_expected_kwh,
        "raw_forecast_today_kwh": getattr(forecast, "raw_forecast_today_kwh", forecast.expected_today_kwh),
        "raw_forecast_so_far_kwh": day_metrics.raw_forecast_so_far_kwh,
        "raw_forecast_tomorrow_kwh": getattr(forecast, "raw_forecast_tomorrow_kwh", expected_tomorrow_kwh),
        "corrected_forecast_today_kwh": getattr(
            forecast, "corrected_forecast_today_kwh", forecast.expected_today_kwh
        ),
        "corrected_forecast_tomorrow_kwh": getattr(
            forecast, "corrected_forecast_tomorrow_kwh", expected_tomorrow_kwh
        ),
        "correction_factor": getattr(forecast, "correction_factor", model_profile.correction_factor),
        "model_state": str(model_state),
        "confidence_score": conf_score,
        "confidence_label": conf_label,
        "historical_samples": getattr(forecast, "historical_samples", model_profile.historical_samples),
        "production_days_observed": production_days,
        "age_seconds": 0.0,
        "freshness": "LIVE",
        "stale": False,
        "points": [
            {
                "timestamp": p.timestamp.isoformat() if hasattr(p.timestamp, "isoformat") else p.timestamp,
                "baseline_power_w": p.baseline_power_w,
                "corrected_power_w": p.corrected_power_w,
                "expected_energy_kwh": p.expected_energy_kwh,
                "lower_bound_power_w": p.lower_bound_power_w,
                "upper_bound_power_w": p.upper_bound_power_w,
                "confidence": p.confidence,
                "correction_factor": p.correction_factor,
            }
            for p in forecast.points
        ],
    }
