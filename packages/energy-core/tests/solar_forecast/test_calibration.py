"""Tests for solar forecast v2 calibration."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from energy_core.config import Settings
from energy_core.solar_forecast.calibration import (
    build_model_profile,
    compute_bias,
    compute_correction_factor,
    compute_mae,
    compute_mape,
    compute_rmse,
    compute_wape,
    metrics_insufficient,
)
from energy_core.solar_forecast.types import (
    MODEL_VERSION,
    ModelState,
    SolarForecastModelProfile,
    SolarForecastObservation,
    resolve_model_state,
)


def _obs(
    day_offset: int,
    *,
    actual: float,
    raw: float,
    corrected: float | None = None,
    eligible: bool = True,
    completeness: float = 99.0,
) -> SolarForecastObservation:
    d = date(2026, 6, 1) + timedelta(days=day_offset)
    corrected = corrected if corrected is not None else raw
    return SolarForecastObservation(
        site_id=1,
        forecast_date=d,
        forecast_kwh_raw=raw,
        forecast_kwh_corrected=corrected,
        actual_kwh=actual,
        data_completeness_pct=completeness,
        training_eligible=eligible,
        model_version=MODEL_VERSION,
    )


def test_resolve_model_state_thresholds():
    settings = Settings()
    assert resolve_model_state(0, settings) == ModelState.NO_DATA
    assert resolve_model_state(1, settings) == ModelState.LEARNING
    assert resolve_model_state(7, settings) == ModelState.PRELIMINARY
    assert resolve_model_state(30, settings) == ModelState.CALIBRATED
    assert resolve_model_state(60, settings) == ModelState.MATURE


def test_zero_samples_metrics_null():
    profile = build_model_profile(1, [], now=datetime(2026, 6, 30, tzinfo=UTC))
    assert profile.historical_samples == 0
    assert profile.model_state == ModelState.NO_DATA
    assert profile.mape_30d is None
    assert profile.mae_30d is None
    assert profile.bias_30d is None
    assert profile.confidence_score is None
    assert metrics_insufficient(profile)


def test_one_sample_learning_state():
    obs = [_obs(0, actual=30, raw=33, corrected=33)]
    profile = build_model_profile(1, obs, now=datetime(2026, 6, 2, tzinfo=UTC))
    assert profile.model_state == ModelState.LEARNING
    assert profile.historical_samples == 1
    assert profile.mape_30d is None
    assert profile.mae_30d is None
    assert profile.confidence_score is None
    assert metrics_insufficient(profile)


def test_thirty_samples_can_be_calibrated():
    obs = [_obs(i, actual=30, raw=33, corrected=30) for i in range(30)]
    profile = build_model_profile(1, obs, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert profile.model_state == ModelState.CALIBRATED
    assert profile.mape_30d is not None


def test_mape_excludes_low_actual_days():
    obs = [
        _obs(0, actual=0.1, raw=5, corrected=5),
        _obs(1, actual=10, raw=10, corrected=10),
    ]
    mape, valid = compute_mape([o for o in obs if o.training_eligible])
    assert valid == 1
    assert mape == 0.0


def test_extreme_outlier_does_not_swing_correction_factor():
    stable = [_obs(i, actual=35, raw=40, corrected=35) for i in range(20)]
    outlier = _obs(21, actual=5, raw=40, corrected=35)
    all_obs = stable + [outlier]
    factor_with = compute_correction_factor(all_obs, previous_factor=1.0, now=datetime(2026, 7, 1, tzinfo=UTC))
    factor_without = compute_correction_factor(stable, previous_factor=1.0, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert abs(factor_with - factor_without) < 0.05


def test_systematic_overforecast_corrects_down():
    obs = [_obs(i, actual=36, raw=40, corrected=40) for i in range(15)]
    factor = compute_correction_factor(obs, previous_factor=1.0, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert factor < 1.0


def test_systematic_underforecast_corrects_up():
    obs = [_obs(i, actual=44, raw=40, corrected=40) for i in range(15)]
    factor = compute_correction_factor(obs, previous_factor=1.0, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert factor > 1.0


def test_site_isolation_in_profile_build():
    site_a = [_obs(0, actual=30, raw=40, corrected=35)]
    site_b_obs = SolarForecastObservation(
        site_id=2,
        forecast_date=date(2026, 6, 1),
        forecast_kwh_raw=10,
        forecast_kwh_corrected=10,
        actual_kwh=20,
        data_completeness_pct=99,
        training_eligible=True,
        model_version=MODEL_VERSION,
    )
    p1 = build_model_profile(1, site_a, now=datetime(2026, 6, 2, tzinfo=UTC))
    p2 = build_model_profile(2, [site_b_obs], now=datetime(2026, 6, 2, tzinfo=UTC))
    assert p1.historical_samples == 1
    assert p2.historical_samples == 1
    assert p1.site_id != p2.site_id


def test_bias_positive_means_overforecast():
    obs = [_obs(0, actual=10, raw=12, corrected=12)]
    bias = compute_bias(obs)
    assert bias is not None
    assert bias > 0


def test_incomplete_data_excluded_from_training():
    obs = [_obs(0, actual=30, raw=33, corrected=33, eligible=False, completeness=50)]
    profile = build_model_profile(1, obs, now=datetime(2026, 6, 2, tzinfo=UTC))
    assert profile.historical_samples == 0


def test_mae_computation():
    obs = [_obs(0, actual=30, raw=33, corrected=32), _obs(1, actual=20, raw=22, corrected=21)]
    mae = compute_mae(obs)
    assert mae == pytest.approx(1.5, abs=0.01)


def test_wape_and_rmse():
    obs = [_obs(i, actual=20, raw=18, corrected=19) for i in range(7)]
    wape = compute_wape(obs)
    rmse = compute_rmse(obs)
    assert wape is not None
    assert rmse is not None
    profile = build_model_profile(1, obs, now=datetime(2026, 6, 30, tzinfo=UTC))
    assert profile.wape_30d is not None
    assert profile.rmse_30d is not None
