"""Tests for forecast accuracy metrics."""

from datetime import UTC, datetime, timedelta

import pytest
from energy_core.solar_forecast.accuracy import EvaluationInput, evaluate_point, summarize_accuracy


def _evaluation(*, actual: float, forecast: float, hour: int = 10):
    return evaluate_point(
        1,
        EvaluationInput(
            bucket_start=datetime(2026, 8, 18, hour, 0, tzinfo=UTC),
            forecasted_energy_kwh=forecast,
            actual_energy_kwh=actual,
            model_version="solar-forecast-v1",
        ),
    )


def test_evaluate_point_computes_absolute_and_percentage_error():
    ev = _evaluation(actual=2.0, forecast=1.5)
    assert ev.absolute_error_kwh == 0.5
    assert ev.percentage_error == 25.0
    assert ev.squared_error == 0.25


def test_evaluate_point_skips_percentage_for_tiny_actual():
    ev = _evaluation(actual=0.005, forecast=0.01)
    assert ev is not None
    assert ev.percentage_error is None


def test_evaluate_point_skips_night_buckets():
    ev = evaluate_point(
        1,
        EvaluationInput(
            bucket_start=datetime(2026, 8, 18, 2, 0, tzinfo=UTC),
            forecasted_energy_kwh=0.0,
            actual_energy_kwh=0.0,
            model_version="solar-forecast-v2",
        ),
        solar_elevation_deg=2.0,
        night_elevation_threshold=5.0,
    )
    assert ev is None


def test_summarize_accuracy_empty_returns_zeros():
    summary = summarize_accuracy([], site_id=1, period_days=7, model_version="v1")
    assert summary.sample_count == 0
    assert summary.mape_pct is None
    assert summary.mae_kwh is None


def test_summarize_accuracy_computes_mape_and_bias():
    evals = [
        _evaluation(actual=2.0, forecast=1.8, hour=10),
        _evaluation(actual=4.0, forecast=3.2, hour=11),
    ]
    summary = summarize_accuracy(evals, site_id=1, period_days=30, model_version="v1")
    assert summary.sample_count == 2
    assert summary.mae_kwh == pytest.approx(0.5)
    assert summary.mape_pct is not None
    assert summary.bias_pct is not None
    assert summary.rmse_kwh is not None
