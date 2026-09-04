"""Tests for forecast learning metrics."""

from datetime import UTC, datetime, timedelta

from energy_core.forecast_learning.metrics import compute_metric_summary
from energy_core.forecast_learning.types import ForecastKind, ForecastSnapshot


def _snap(predicted: float, actual: float | None, kind: ForecastKind = ForecastKind.LOAD_W) -> ForecastSnapshot:
    start = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
    return ForecastSnapshot(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        kind=kind,
        predicted_value=predicted,
        actual_value=actual,
        forecast_recorded_at=start - timedelta(hours=1),
        actual_recorded_at=start + timedelta(minutes=15) if actual is not None else None,
    )


def test_compute_metric_summary_empty():
    summary = compute_metric_summary(ForecastKind.LOAD_W, ())
    assert summary.sample_count == 0
    assert summary.mae is None
    assert summary.bias is None
    assert summary.mape_pct is None


def test_compute_metric_summary_mae_and_bias():
    snapshots = (
        _snap(1000.0, 1200.0),
        _snap(2000.0, 1800.0),
    )
    summary = compute_metric_summary(ForecastKind.LOAD_W, snapshots)
    assert summary.sample_count == 2
    assert summary.mae == 200.0
    assert summary.bias == 0.0
    assert summary.mape_pct is not None


def test_compute_metric_summary_skips_mape_near_zero_solar():
    snapshots = (
        _snap(10.0, 5.0, kind=ForecastKind.SOLAR_W),
        _snap(20.0, 15.0, kind=ForecastKind.SOLAR_W),
    )
    summary = compute_metric_summary(ForecastKind.SOLAR_W, snapshots)
    assert summary.sample_count == 2
    assert summary.mape_pct is None


def test_compute_metric_summary_price_mape():
    snapshots = (
        _snap(1.0, 1.1, kind=ForecastKind.IMPORT_PRICE_SEK_KWH),
        _snap(0.8, 0.72, kind=ForecastKind.IMPORT_PRICE_SEK_KWH),
    )
    summary = compute_metric_summary(ForecastKind.IMPORT_PRICE_SEK_KWH, snapshots)
    assert summary.sample_count == 2
    assert summary.mape_pct is not None
