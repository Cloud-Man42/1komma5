"""Solar forecast v2 calibration — metrics, correction factor, confidence."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from energy_core.config import Settings, get_settings
from energy_core.solar_forecast.historical import cloud_bucket, recency_weight
from energy_core.solar_forecast.types import (
    MODEL_VERSION,
    ModelState,
    SolarForecastModelProfile,
    SolarForecastObservation,
    confidence_label_from_score,
    resolve_model_state,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WindowMetrics:
    mae: float | None
    mape: float | None
    bias: float | None
    valid_mape_days: int
    sample_count: int


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    raw_mae: float | None
    corrected_mae: float | None
    improvement_pct: float | None


def weather_condition_bucket(cloud_cover_avg: float | None) -> str:
    return cloud_bucket(cloud_cover_avg)


def is_outlier_ratio(ratio: float, settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return ratio < cfg.solar_forecast_outlier_ratio_min or ratio > cfg.solar_forecast_outlier_ratio_max


def clamp_correction_factor(value: float, settings: Settings | None = None) -> float:
    cfg = settings or get_settings()
    return max(cfg.solar_forecast_correction_factor_min, min(cfg.solar_forecast_correction_factor_max, value))


def compute_mae(
    observations: list[SolarForecastObservation],
    *,
    use_raw: bool = False,
) -> float | None:
    errors: list[float] = []
    for obs in observations:
        if obs.actual_kwh is None:
            continue
        forecast = obs.forecast_kwh_raw if use_raw else obs.forecast_kwh_corrected
        if forecast is None:
            continue
        errors.append(abs(obs.actual_kwh - forecast))
    if not errors:
        return None
    return sum(errors) / len(errors)


def compute_mape(
    observations: list[SolarForecastObservation],
    *,
    use_raw: bool = False,
    settings: Settings | None = None,
) -> tuple[float | None, int]:
    cfg = settings or get_settings()
    pct_errors: list[float] = []
    for obs in observations:
        if obs.actual_kwh is None or obs.actual_kwh < cfg.solar_forecast_mape_min_actual_kwh:
            continue
        forecast = obs.forecast_kwh_raw if use_raw else obs.forecast_kwh_corrected
        if forecast is None:
            continue
        pct_errors.append(abs(obs.actual_kwh - forecast) / obs.actual_kwh * 100.0)
    if not pct_errors:
        return None, 0
    return sum(pct_errors) / len(pct_errors), len(pct_errors)


def compute_bias(
    observations: list[SolarForecastObservation],
    *,
    use_raw: bool = False,
) -> float | None:
    """Normalized mean bias: sum(forecast - actual) / sum(actual) * 100.

    Positive bias means the model over-forecasts.
    """
    sum_actual = 0.0
    sum_signed = 0.0
    for obs in observations:
        if obs.actual_kwh is None or obs.actual_kwh <= 0:
            continue
        forecast = obs.forecast_kwh_raw if use_raw else obs.forecast_kwh_corrected
        if forecast is None:
            continue
        sum_actual += obs.actual_kwh
        sum_signed += forecast - obs.actual_kwh
    if sum_actual <= 0:
        return None
    return sum_signed / sum_actual * 100.0


def compute_window_metrics(
    observations: list[SolarForecastObservation],
    *,
    settings: Settings | None = None,
) -> WindowMetrics:
    eligible = [o for o in observations if o.training_eligible and o.actual_kwh is not None]
    mape, valid_days = compute_mape(eligible, settings=settings)
    return WindowMetrics(
        mae=compute_mae(eligible),
        mape=mape,
        bias=compute_bias(eligible),
        valid_mape_days=valid_days,
        sample_count=len(eligible),
    )


def compute_benchmark(observations: list[SolarForecastObservation]) -> BenchmarkMetrics:
    eligible = [o for o in observations if o.training_eligible and o.actual_kwh is not None]
    raw_mae = compute_mae(eligible, use_raw=True)
    corrected_mae = compute_mae(eligible, use_raw=False)
    improvement = None
    if raw_mae is not None and corrected_mae is not None and raw_mae > 0:
        improvement = (raw_mae - corrected_mae) / raw_mae * 100.0
    return BenchmarkMetrics(raw_mae=raw_mae, corrected_mae=corrected_mae, improvement_pct=improvement)


def _weighted_ratios(
    observations: list[SolarForecastObservation],
    *,
    now: datetime,
    settings: Settings | None = None,
) -> list[tuple[float, float]]:
    cfg = settings or get_settings()
    pairs: list[tuple[float, float]] = []
    for obs in observations:
        if not obs.training_eligible:
            continue
        if obs.actual_kwh is None or obs.forecast_kwh_raw is None or obs.forecast_kwh_raw <= 0:
            continue
        if obs.data_completeness_pct is not None and obs.data_completeness_pct < cfg.solar_forecast_min_data_completeness_pct:
            continue
        ratio = obs.actual_kwh / obs.forecast_kwh_raw
        if is_outlier_ratio(ratio, cfg):
            continue
        age_days = (now.date() - obs.forecast_date).days
        weight = recency_weight(float(age_days), now.month, obs.forecast_date.month)
        pairs.append((ratio, weight))
    return pairs


def _weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return sum(r for r, _ in pairs) / len(pairs)
    return sum(r * w for r, w in pairs) / total_w


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        return sorted_vals[mid]
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def compute_correction_factor(
    observations: list[SolarForecastObservation],
    *,
    previous_factor: float = 1.0,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> float:
    cfg = settings or get_settings()
    now = now or datetime.now(UTC)
    pairs = _weighted_ratios(observations, now=now, settings=cfg)
    if not pairs:
        return previous_factor

    ratios = [r for r, _ in pairs]
    median_ratio = _median(ratios)
    if median_ratio is None:
        return previous_factor

    alpha = cfg.solar_forecast_correction_ema_alpha
    ema = previous_factor + alpha * (median_ratio - previous_factor)
    return clamp_correction_factor(ema, cfg)


def compute_confidence_score(
    profile: SolarForecastModelProfile,
    *,
    settings: Settings | None = None,
) -> float | None:
    if profile.historical_samples <= 0:
        return None

    cfg = settings or get_settings()
    sample_score = min(100.0, profile.historical_samples / cfg.solar_forecast_min_samples_mature * 100.0)

    mape_score = 50.0
    if profile.mape_30d is not None:
        mape_score = max(0.0, 100.0 - profile.mape_30d * 2.0)

    mae_score = 50.0
    if profile.mae_30d is not None:
        mae_score = max(0.0, 100.0 - profile.mae_30d * 10.0)

    bias_score = 50.0
    if profile.bias_30d is not None:
        bias_score = max(0.0, 100.0 - abs(profile.bias_30d) * 2.0)

    stability = 100.0
    if profile.correction_factor != 1.0:
        deviation = abs(profile.correction_factor - 1.0)
        stability = max(50.0, 100.0 - deviation * 100.0)

    score = sample_score * 0.35 + mape_score * 0.25 + mae_score * 0.15 + bias_score * 0.15 + stability * 0.10
    return round(min(100.0, max(0.0, score)), 1)


def build_model_profile(
    site_id: int,
    observations: list[SolarForecastObservation],
    *,
    previous: SolarForecastModelProfile | None = None,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> SolarForecastModelProfile:
    cfg = settings or get_settings()
    now = now or datetime.now(UTC)
    prev = previous or SolarForecastModelProfile(site_id=site_id)

    training = [o for o in observations if o.training_eligible and o.actual_kwh is not None]
    historical_samples = len(training)

    def window(days: int) -> list[SolarForecastObservation]:
        cutoff = now.date().toordinal() - days
        return [o for o in training if o.forecast_date.toordinal() >= cutoff]

    m7 = compute_window_metrics(window(7), settings=cfg)
    m30 = compute_window_metrics(window(30), settings=cfg)
    m90 = compute_window_metrics(window(90), settings=cfg)
    bench = compute_benchmark(window(30))

    min_for_metrics = cfg.solar_forecast_min_samples_preliminary
    state = resolve_model_state(historical_samples, cfg)

    def metrics_publishable() -> bool:
        return state not in (ModelState.NO_DATA, ModelState.LEARNING) and historical_samples >= min_for_metrics

    def gated(value: float | None, count: int) -> float | None:
        if not metrics_publishable() or count < 1:
            return None
        return value

    new_factor = compute_correction_factor(
        training,
        previous_factor=prev.correction_factor,
        now=now,
        settings=cfg,
    )
    if prev.correction_factor != new_factor:
        logger.info(
            "Correction factor updated site_id=%s old=%.3f new=%.3f",
            site_id,
            prev.correction_factor,
            new_factor,
        )

    profile = SolarForecastModelProfile(
        site_id=site_id,
        model_version=MODEL_VERSION,
        historical_samples=historical_samples,
        model_state=state,
        mape_7d=gated(m7.mape, m7.valid_mape_days),
        mape_30d=gated(m30.mape, m30.valid_mape_days),
        mape_90d=gated(m90.mape, m90.valid_mape_days),
        mape_7d_valid_days=m7.valid_mape_days,
        mape_30d_valid_days=m30.valid_mape_days,
        mape_90d_valid_days=m90.valid_mape_days,
        mae_7d=gated(m7.mae, m7.sample_count),
        mae_30d=gated(m30.mae, m30.sample_count),
        mae_90d=gated(m90.mae, m90.sample_count),
        bias_7d=gated(m7.bias, m7.sample_count),
        bias_30d=gated(m30.bias, m30.sample_count),
        bias_90d=gated(m90.bias, m90.sample_count),
        raw_mae_30d=gated(bench.raw_mae, m30.sample_count),
        corrected_mae_30d=gated(bench.corrected_mae, m30.sample_count),
        improvement_pct_30d=gated(bench.improvement_pct, m30.sample_count),
        correction_factor=new_factor,
        seasonal_factors=prev.seasonal_factors,
        last_training_at=now if historical_samples > 0 else prev.last_training_at,
        last_evaluation_at=now,
        created_at=prev.created_at or now,
        updated_at=now,
    )
    confidence = compute_confidence_score(profile, settings=cfg) if metrics_publishable() else None
    profile = replace(profile, confidence_score=confidence)

    if prev.model_state != profile.model_state:
        logger.info(
            "Model state changed site_id=%s old=%s new=%s samples=%d",
            site_id,
            prev.model_state,
            profile.model_state,
            historical_samples,
        )

    return profile


def metrics_insufficient(profile: SolarForecastModelProfile, settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    if profile.model_state == ModelState.NO_DATA or profile.historical_samples <= 0:
        return True
    if profile.model_state == ModelState.LEARNING:
        return True
    return profile.historical_samples < cfg.solar_forecast_min_samples_preliminary


__all__ = [
    "BenchmarkMetrics",
    "WindowMetrics",
    "build_model_profile",
    "clamp_correction_factor",
    "compute_bias",
    "compute_confidence_score",
    "compute_correction_factor",
    "compute_mae",
    "compute_mape",
    "confidence_label_from_score",
    "is_outlier_ratio",
    "metrics_insufficient",
    "weather_condition_bucket",
]
