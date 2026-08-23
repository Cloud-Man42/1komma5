"""Forecast accuracy tracking and metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from energy_core.solar_forecast.types import ForecastAccuracySummary, ForecastEvaluation


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    bucket_start: datetime
    forecasted_energy_kwh: float
    actual_energy_kwh: float
    model_version: str


def evaluate_point(
    site_id: int,
    inp: EvaluationInput,
) -> ForecastEvaluation:
    forecast_ts = inp.bucket_start
    actual = inp.actual_energy_kwh
    forecast = inp.forecasted_energy_kwh
    abs_err = abs(actual - forecast)
    pct = (abs_err / actual * 100.0) if actual > 0.01 else None
    sq = (actual - forecast) ** 2
    return ForecastEvaluation(
        site_id=site_id,
        forecast_timestamp=forecast_ts,
        bucket_start=inp.bucket_start,
        forecasted_energy_kwh=forecast,
        actual_energy_kwh=actual,
        absolute_error_kwh=abs_err,
        percentage_error=pct,
        squared_error=sq,
        model_version=inp.model_version,
    )


def summarize_accuracy(
    evaluations: list[ForecastEvaluation],
    *,
    site_id: int,
    period_days: int,
    model_version: str,
    min_energy_kwh: float = 0.05,
) -> ForecastAccuracySummary:
    if not evaluations:
        return ForecastAccuracySummary(
            site_id=site_id,
            period_days=period_days,
            mae_kwh=None,
            mape_pct=None,
            rmse_kwh=None,
            bias_pct=None,
            sample_count=0,
            model_version=model_version,
        )

    abs_errors = [e.absolute_error_kwh for e in evaluations]
    mae = sum(abs_errors) / len(abs_errors)

    mape_samples = [
        e.percentage_error
        for e in evaluations
        if e.actual_energy_kwh >= min_energy_kwh and e.percentage_error is not None
    ]
    mape = sum(mape_samples) / len(mape_samples) if mape_samples else None

    rmse = (sum(e.squared_error for e in evaluations) / len(evaluations)) ** 0.5

    bias_samples = [
        (e.forecasted_energy_kwh - e.actual_energy_kwh) / e.actual_energy_kwh * 100.0
        for e in evaluations
        if e.actual_energy_kwh >= min_energy_kwh
    ]
    bias = sum(bias_samples) / len(bias_samples) if bias_samples else None

    return ForecastAccuracySummary(
        site_id=site_id,
        period_days=period_days,
        mae_kwh=mae,
        mape_pct=mape,
        rmse_kwh=rmse,
        bias_pct=bias,
        sample_count=len(evaluations),
        model_version=model_version,
    )


def filter_evaluations_since(
    evaluations: list[ForecastEvaluation],
    since: datetime,
) -> list[ForecastEvaluation]:
    return [e for e in evaluations if e.bucket_start >= since]
