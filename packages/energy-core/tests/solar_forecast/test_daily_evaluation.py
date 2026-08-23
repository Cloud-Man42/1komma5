"""Tests for daily solar forecast evaluation."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from energy_core.solar_forecast.daily_evaluation import (
    actual_kwh_for_day,
    build_observation_from_day,
    days_in_evaluation_window,
    days_to_evaluate,
    determine_training_eligibility,
    evaluate_observation_errors,
)
from energy_core.solar_forecast.types import MODEL_VERSION, SolarForecast, SolarForecastPoint


def _reading(ts: datetime, solar_w: float) -> tuple[datetime, float, float]:
    return (ts, solar_w, 1000.0)


def test_days_to_evaluate_returns_yesterday():
    now = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    days = days_to_evaluate("Europe/Stockholm", now)
    assert len(days) >= 1


def test_days_in_evaluation_window_excludes_today():
    now = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    days = days_in_evaluation_window("Europe/Stockholm", now=now, window_days=7)
    assert len(days) == 7
    assert date(2026, 6, 14) in days
    assert date(2026, 6, 15) not in days


def test_actual_kwh_for_day_sums_buckets():
    day = date(2026, 6, 15)
    start = datetime(2026, 6, 15, 8, 0, tzinfo=UTC)
    readings = [_reading(start + timedelta(minutes=i * 15), 4000.0) for i in range(4)]
    actual, completeness = actual_kwh_for_day(readings, day, "UTC")
    assert actual > 0
    assert completeness > 0


def test_evaluate_observation_errors():
    errors = evaluate_observation_errors(actual_kwh=30, raw_kwh=33, corrected_kwh=31)
    assert errors["absolute_error_kwh"] == 1.0
    assert errors["raw_absolute_error_kwh"] == 3.0


def test_incomplete_actual_excluded():
    eligible, reason = determine_training_eligibility(
        actual_kwh=10,
        data_completeness_pct=80,
        raw_kwh=12,
    )
    assert eligible is False
    assert reason == "incomplete_data"


def test_build_observation_from_day():
    now = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    forecast = SolarForecast(
        site_id=1,
        generated_at=now,
        model_version=MODEL_VERSION,
        quality="MEDIUM",
        weather_source="live",
        expected_today_kwh=20,
        remaining_today_kwh=10,
        expected_tomorrow_kwh=25,
        peak_power_w=5000,
        peak_time=now,
        confidence=0.7,
        lower_today_kwh=15,
        upper_today_kwh=25,
        weather_summary="Partly cloudy",
        points=tuple(
            SolarForecastPoint(
                timestamp=now,
                baseline_power_w=4000,
                corrected_power_w=3800,
                expected_energy_kwh=1.0,
                lower_bound_power_w=3000,
                upper_bound_power_w=4500,
                confidence=0.7,
            )
            for _ in range(4)
        ),
    )
    obs = build_observation_from_day(
        1,
        date(2026, 6, 15),
        forecast=forecast,
        actual_kwh=18.0,
        data_completeness_pct=99.0,
        timezone="UTC",
    )
    assert obs.actual_kwh == 18.0
    assert obs.forecast_kwh_raw is not None
    # raw ~4 kWh vs actual 18 kWh triggers outlier exclusion by design
    assert obs.training_eligible is False
    assert obs.exclusion_reason == "outlier_ratio"
