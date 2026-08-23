"""Tests for historical correction engine."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.solar_forecast.correction import SolarForecastCorrectionEngine, build_profile
from energy_core.solar_forecast.historical import build_performance_sample
from energy_core.solar_forecast.types import (
    PerformanceSample,
    SitePerformanceProfile,
    WeatherForecastPoint,
)


def test_correction_trends_toward_historical_ratio() -> None:
    samples = [
        PerformanceSample(
            timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
            baseline_energy_kwh=10.0,
            actual_energy_kwh=9.0,
            performance_ratio=0.9,
            month=6,
            hour=12,
            irradiance_bucket="high",
            cloud_bucket="clear",
        )
        for _ in range(20)
    ]
    profile = build_profile(samples)
    profile = SitePerformanceProfile(
        site_id=1, global_factor=profile.global_factor, sample_count=20
    )
    engine = SolarForecastCorrectionEngine()
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 2, 12, 0, tzinfo=UTC), gti_wm2=800.0)
    factor = engine.correction_factor(profile, point, point.timestamp)
    assert 0.85 <= factor <= 0.95


def test_no_history_uses_factor_one() -> None:
    profile = SitePerformanceProfile(site_id=1, sample_count=0)
    engine = SolarForecastCorrectionEngine()
    point = WeatherForecastPoint(timestamp=datetime(2026, 6, 2, 12, 0, tzinfo=UTC), gti_wm2=800.0)
    assert engine.correction_factor(profile, point, point.timestamp) == 1.0


def test_anomaly_excluded_from_samples() -> None:
    sample = build_performance_sample(
        bucket_start=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
        actual_kwh=0.0,
        baseline_kwh=25.0,
        weather=WeatherForecastPoint(
            timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC), gti_wm2=900.0
        ),
        coverage=0.9,
    )
    assert sample is None
