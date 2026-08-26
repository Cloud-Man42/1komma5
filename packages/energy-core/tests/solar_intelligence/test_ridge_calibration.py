"""Tests for Ridge calibration."""

from datetime import date

import pytest

from energy_core.solar_intelligence.calibration import SolarCalibrationService, build_feature_vector
from energy_core.solar_intelligence.types import TrainingSample, SampleQuality

pytest.importorskip("sklearn")


def _sample(hour: int, actual: float, physical: float, day: date = date(2026, 6, 1)) -> TrainingSample:
    return TrainingSample(
        site_id=1,
        sample_date=day,
        hour_utc=hour,
        actual_kwh=actual,
        physical_kwh=physical,
        ghi_wm2=500.0,
        dni_wm2=400.0,
        dhi_wm2=100.0,
        poa_wm2=480.0,
        solar_elevation_deg=45.0,
        cloud_cover_pct=20.0,
        temperature_c=22.0,
        quality=SampleQuality.GOOD,
    )


def test_build_feature_vector_length():
    s = _sample(10, 1.0, 0.9)
    vec = build_feature_vector(s, installed_kwp=10.0, tilt=35.0, azimuth=180.0)
    assert len(vec) == 12


def test_train_insufficient_samples_returns_none():
    svc = SolarCalibrationService()
    result = svc.train(1, [_sample(10, 1.0, 0.9)], installed_kwp=10.0, tilt=35.0, azimuth=180.0)
    assert result is None


def test_train_with_enough_samples():
    svc = SolarCalibrationService()
    samples = [_sample(h, 0.5 + h * 0.01, 0.45 + h * 0.01) for h in range(8)]
    result = svc.train(1, samples, installed_kwp=10.0, tilt=35.0, azimuth=180.0)
    assert result is not None
    assert result.sample_count >= 8
    assert "intercept" in result.coefficients
