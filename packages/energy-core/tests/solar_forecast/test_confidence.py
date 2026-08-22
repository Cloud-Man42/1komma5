"""Tests for solar forecast confidence."""

from __future__ import annotations

from energy_core.solar_forecast.confidence import SolarForecastConfidenceService
from energy_core.solar_forecast.types import SitePerformanceProfile


def test_high_confidence_with_stable_history() -> None:
    svc = SolarForecastConfidenceService()
    profile = SitePerformanceProfile(site_id=1, sample_count=200, mape_30d=8.0)
    conf = svc.compute_point_confidence(
        hours_ahead=2.0,
        weather_source="live",
        profile=profile,
        cloud_var=0.1,
    )
    assert conf >= 0.75
    assert svc.quality_from_confidence(conf) in {"HIGH", "MEDIUM"}


def test_low_confidence_with_little_history_and_fallback() -> None:
    svc = SolarForecastConfidenceService()
    profile = SitePerformanceProfile(site_id=1, sample_count=2)
    conf = svc.compute_point_confidence(
        hours_ahead=36.0,
        weather_source="fallback",
        profile=profile,
        cloud_var=0.8,
    )
    assert conf < 0.6
    assert svc.quality_from_confidence(conf) in {"LOW", "INSUFFICIENT_DATA"}
