"""Map solar forecast API snapshot payloads to response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def payload_to_solar_forecast_response(payload: dict[str, Any], response_cls, point_cls):
    """Convert persisted JSON payload to a Pydantic SolarForecastResponse."""
    points = [
        point_cls(
            timestamp=_parse_dt(p.get("timestamp")),
            baseline_power_w=p.get("baseline_power_w"),
            corrected_power_w=p.get("corrected_power_w"),
            expected_energy_kwh=p.get("expected_energy_kwh"),
            lower_bound_power_w=p.get("lower_bound_power_w"),
            upper_bound_power_w=p.get("upper_bound_power_w"),
            confidence=p.get("confidence"),
            correction_factor=p.get("correction_factor"),
        )
        for p in payload.get("points") or []
    ]
    peak_time = payload.get("peak_time")
    snapshot_generated_at = payload.get("snapshot_generated_at")
    return response_cls(
        site_id=int(payload["site_id"]),
        generated_at=_parse_dt(payload["generated_at"]),
        model_version=payload.get("model_version", ""),
        quality=payload.get("quality", ""),
        weather_source=payload.get("weather_source", ""),
        expected_today_kwh=float(payload.get("expected_today_kwh") or 0),
        remaining_today_kwh=float(payload.get("remaining_today_kwh") or 0),
        expected_tomorrow_kwh=payload.get("expected_tomorrow_kwh"),
        peak_power_w=float(payload.get("peak_power_w") or 0),
        peak_time=_parse_dt(peak_time) if peak_time else None,
        confidence=float(payload.get("confidence") or 0),
        lower_today_kwh=float(payload.get("lower_today_kwh") or 0),
        upper_today_kwh=float(payload.get("upper_today_kwh") or 0),
        weather_summary=payload.get("weather_summary") or "",
        actual_today_kwh=float(payload.get("actual_today_kwh") or 0),
        forecast_so_far_kwh=float(payload.get("forecast_so_far_kwh") or 0),
        remaining_vs_expected_kwh=float(payload.get("remaining_vs_expected_kwh") or 0),
        raw_forecast_today_kwh=float(payload.get("raw_forecast_today_kwh") or 0),
        raw_forecast_so_far_kwh=float(payload.get("raw_forecast_so_far_kwh") or 0),
        raw_forecast_tomorrow_kwh=payload.get("raw_forecast_tomorrow_kwh"),
        corrected_forecast_today_kwh=float(payload.get("corrected_forecast_today_kwh") or 0),
        corrected_forecast_tomorrow_kwh=payload.get("corrected_forecast_tomorrow_kwh"),
        correction_factor=float(payload.get("correction_factor") or 1.0),
        model_state=str(payload.get("model_state") or "NO_DATA"),
        confidence_score=payload.get("confidence_score"),
        confidence_label=payload.get("confidence_label"),
        historical_samples=int(payload.get("historical_samples") or 0),
        production_days_observed=int(payload.get("production_days_observed") or 0),
        age_seconds=float(payload.get("age_seconds") or 0),
        freshness=str(payload.get("freshness") or "LIVE"),
        stale=bool(payload.get("stale")),
        snapshot_generated_at=_parse_dt(snapshot_generated_at) if snapshot_generated_at else None,
        points=points,
    )


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Expected datetime or str, got {type(value)!r}")
