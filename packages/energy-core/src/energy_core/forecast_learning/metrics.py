"""Forecast accuracy metrics."""

from __future__ import annotations

from statistics import mean

from energy_core.forecast_learning.types import ForecastKind, ForecastMetricSummary, ForecastSnapshot


def _min_denominator(kind: ForecastKind) -> float:
    if kind == ForecastKind.IMPORT_PRICE_SEK_KWH:
        return 0.05
    return 50.0


def compute_metric_summary(
    kind: ForecastKind,
    snapshots: tuple[ForecastSnapshot, ...],
) -> ForecastMetricSummary:
    pairs = [
        (s.predicted_value, s.actual_value)
        for s in snapshots
        if s.actual_value is not None and s.kind == kind
    ]
    if not pairs:
        return ForecastMetricSummary(kind=kind, mae=None, bias=None, sample_count=0, mape_pct=None)

    errors = [actual - predicted for predicted, actual in pairs]
    abs_errors = [abs(e) for e in errors]
    mae = mean(abs_errors)
    bias = mean(errors)
    min_denom = _min_denominator(kind)
    mape_values: list[float] = []
    for predicted, actual in pairs:
        if abs(actual) >= min_denom:
            mape_values.append(abs(actual - predicted) / abs(actual) * 100.0)
    mape_pct = mean(mape_values) if mape_values else None
    return ForecastMetricSummary(
        kind=kind,
        mae=mae,
        bias=bias,
        sample_count=len(pairs),
        mape_pct=mape_pct,
    )
