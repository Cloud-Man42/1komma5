from datetime import date

import pytest

from energy_core.solar_forecast.performance import (
    average_ratio,
    build_performance_summary,
    observation_to_performance_day,
    performance_days_from_observations,
    performance_ratio,
    today_deviation_pct,
)
from energy_core.solar_forecast.types import SolarForecastObservation


def _obs(**kwargs) -> SolarForecastObservation:
    defaults = {
        "site_id": 1,
        "forecast_date": date(2026, 8, 20),
        "forecast_kwh_raw": 20.0,
        "forecast_kwh_corrected": 18.0,
        "actual_kwh": 18.5,
        "training_eligible": True,
        "model_version": "solar-forecast-v2",
    }
    defaults.update(kwargs)
    return SolarForecastObservation(**defaults)


def test_performance_ratio_requires_meaningful_expected():
    assert performance_ratio(10.0, 20.0) == 0.5
    assert performance_ratio(10.0, 0.2) is None
    assert performance_ratio(None, 20.0) is None


def test_observation_to_performance_day_uses_corrected_forecast():
    row = observation_to_performance_day(_obs(actual_kwh=18.0))
    assert row is not None
    assert row["performance_ratio"] == 1.0
    assert row["expected_kwh"] == 18.0


def test_observation_to_performance_day_falls_back_to_raw_without_corrected():
    row = observation_to_performance_day(
        _obs(forecast_kwh_corrected=None, forecast_kwh_raw=22.0, actual_kwh=20.0)
    )
    assert row is not None
    assert row["expected_kwh"] == 22.0
    assert row["performance_ratio"] == pytest.approx(20 / 22, rel=1e-3)


def test_observation_to_performance_day_skips_missing_baseline():
    assert observation_to_performance_day(
        _obs(forecast_kwh_corrected=None, forecast_kwh_raw=0.0, actual_kwh=5.0)
    ) is None
    assert observation_to_performance_day(
        _obs(forecast_kwh_corrected=None, forecast_kwh_raw=None, physical_kwh=None)
    ) is None


def test_performance_days_from_observations_filters_invalid_rows():
    days = performance_days_from_observations(
        [
            _obs(
                forecast_date=date(2026, 8, 18),
                forecast_kwh_corrected=10.0,
                forecast_kwh_raw=12.0,
                actual_kwh=9.0,
            ),
            _obs(
                forecast_date=date(2026, 8, 19),
                forecast_kwh_corrected=None,
                forecast_kwh_raw=0.0,
                actual_kwh=9.0,
            ),
            _obs(
                forecast_date=date(2026, 8, 20),
                forecast_kwh_corrected=10.0,
                forecast_kwh_raw=12.0,
                actual_kwh=9.5,
            ),
        ]
    )
    assert len(days) == 2
    assert days[0]["date"] == "2026-08-18"
    assert days[1]["performance_ratio"] == 0.95


def test_average_ratio_and_summary():
    days = performance_days_from_observations(
        [
            _obs(
                forecast_date=date(2026, 8, 18),
                forecast_kwh_corrected=10.0,
                forecast_kwh_raw=12.0,
                actual_kwh=9.0,
            ),
            _obs(
                forecast_date=date(2026, 8, 19),
                forecast_kwh_corrected=10.0,
                forecast_kwh_raw=12.0,
                actual_kwh=9.5,
            ),
        ]
    )
    assert average_ratio(days, last_n=7) == 0.925
    summary = build_performance_summary(days, actual_today_kwh=4.0, raw_forecast_so_far_kwh=8.0)
    assert summary["headline_ratio"] == 0.925
    assert summary["week_avg"] == 0.925
    assert summary["today_deviation_pct"] == -50.0


def test_today_deviation_pct():
    assert today_deviation_pct(9.0, 10.0) == -10.0
    assert today_deviation_pct(11.0, 10.0) == 10.0
    assert today_deviation_pct(1.0, 0.1) is None


def test_estimate_raw_so_far_from_totals():
    from energy_core.solar_forecast.performance import estimate_raw_so_far_from_totals

    assert estimate_raw_so_far_from_totals(
        raw_today_kwh=40.0,
        corrected_so_far_kwh=10.0,
        corrected_today_kwh=20.0,
    ) == 20.0
