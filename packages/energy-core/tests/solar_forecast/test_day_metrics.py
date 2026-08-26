"""Tests for intraday solar forecast metrics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics
from energy_core.solar_forecast.types import SolarForecast, SolarForecastPoint


def _point(at: datetime, power_w: float, energy_kwh: float = 0.25) -> SolarForecastPoint:
    return SolarForecastPoint(
        timestamp=at,
        baseline_power_w=power_w,
        corrected_power_w=power_w,
        expected_energy_kwh=energy_kwh,
        lower_bound_power_w=0.0,
        upper_bound_power_w=power_w * 2,
        confidence=0.8,
    )


def test_compute_solar_day_metrics_splits_past_and_future() -> None:
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    points = (
        _point(datetime(2026, 8, 26, 8, 0, tzinfo=UTC), 2000.0, 0.5),
        _point(datetime(2026, 8, 26, 9, 0, tzinfo=UTC), 3000.0, 0.75),
        _point(datetime(2026, 8, 26, 11, 0, tzinfo=UTC), 4000.0, 1.0),
        _point(datetime(2026, 8, 26, 12, 0, tzinfo=UTC), 1000.0, 0.25),
    )
    forecast = SolarForecast(
        site_id=1,
        generated_at=now - timedelta(hours=1),
        model_version="test",
        quality="MEDIUM",
        weather_source="live",
        expected_today_kwh=999.0,
        remaining_today_kwh=999.0,
        expected_tomorrow_kwh=None,
        peak_power_w=1000.0,
        peak_time=points[-1].timestamp,
        confidence=0.8,
        lower_today_kwh=0.0,
        upper_today_kwh=10.0,
        weather_summary="Test",
        points=points,
    )

    metrics = compute_solar_day_metrics(forecast, timezone="Europe/Stockholm", now=now)

    assert metrics.forecast_so_far_kwh == 1.25
    assert metrics.remaining_today_kwh == 1.25
    assert metrics.expected_today_kwh == 2.5
    assert metrics.peak_power_w == 4000.0
    assert metrics.peak_time == points[2].timestamp
