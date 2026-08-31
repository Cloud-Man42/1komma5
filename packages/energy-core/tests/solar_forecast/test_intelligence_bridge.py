"""Tests for intelligence → v2 forecast bridge."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from energy_core.solar_forecast.intelligence_bridge import (
    compose_solar_forecast,
    intelligence_to_v2_points,
)
from energy_core.solar_forecast.types import SolarForecastPoint, SolarSiteConfiguration
from energy_core.solar_intelligence.types import (
    ForecastStatus,
    HourlyForecastPoint,
    IntelligenceForecast,
    INTELLIGENCE_MODEL_VERSION,
)


def _site() -> SolarSiteConfiguration:
    return SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.2,
        installed_peak_power_kw=10.0,
        timezone="Europe/Stockholm",
        enabled=True,
    )


def _intelligence(*, hourly: tuple[HourlyForecastPoint, ...]) -> IntelligenceForecast:
    now = datetime(2026, 8, 29, 8, 0, tzinfo=UTC)
    return IntelligenceForecast(
        site_id=1,
        generated_at=now,
        model_version=INTELLIGENCE_MODEL_VERSION,
        status=ForecastStatus.HEALTHY,
        expected_today_kwh=14.5,
        remaining_today_kwh=8.0,
        expected_tomorrow_kwh=12.0,
        expected_day_after_kwh=11.0,
        peak_power_w=4200.0,
        peak_time=now,
        lower_today_kwh=12.0,
        upper_today_kwh=17.0,
        confidence=0.82,
        confidence_label="High",
        radiation_confidence="HIGH",
        hourly=hourly,
        physical_today_kwh=13.0,
        learned_correction_pct=5.0,
        weather_source="smhi-strang",
    )


def test_intelligence_to_v2_points_uses_hourly_energy():
    ts = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    intel = _intelligence(
        hourly=(
            HourlyForecastPoint(
                timestamp=ts,
                physical_w=3000.0,
                corrected_w=3300.0,
                lower_w=2800.0,
                upper_w=3600.0,
                confidence=0.8,
                ghi_wm2=500.0,
            ),
        )
    )

    points = intelligence_to_v2_points(intel)
    assert len(points) == 1
    assert points[0].expected_energy_kwh == pytest.approx(3.3)
    assert points[0].corrected_power_w == 3300.0


def test_compose_solar_forecast_merges_extended_without_duplicates():
    ts1 = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    ts2 = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    intel = _intelligence(
        hourly=(
            HourlyForecastPoint(
                timestamp=ts1,
                physical_w=2000.0,
                corrected_w=2200.0,
                lower_w=1800.0,
                upper_w=2400.0,
                confidence=0.7,
            ),
        )
    )
    extended = (
        SolarForecastPoint(
            timestamp=ts1,
            baseline_power_w=2000.0,
            corrected_power_w=2200.0,
            expected_energy_kwh=2.2,
            lower_bound_power_w=1800.0,
            upper_bound_power_w=2400.0,
            confidence=0.7,
        ),
        SolarForecastPoint(
            timestamp=ts2,
            baseline_power_w=1500.0,
            corrected_power_w=1500.0,
            expected_energy_kwh=1.5,
            lower_bound_power_w=1200.0,
            upper_bound_power_w=1800.0,
            confidence=0.4,
        ),
    )

    forecast = compose_solar_forecast(_site(), intel, extended)
    assert forecast.model_version == "solar-forecast-v2"
    assert forecast.expected_today_kwh == 14.5
    assert len(forecast.points) == 2
    assert forecast.points[0].timestamp == ts1
    assert forecast.points[1].timestamp == ts2


def test_compose_solar_forecast_maps_degraded_quality():
    ts = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    intel = IntelligenceForecast(
        site_id=1,
        generated_at=ts,
        model_version=INTELLIGENCE_MODEL_VERSION,
        status=ForecastStatus.DEGRADED,
        expected_today_kwh=5.0,
        remaining_today_kwh=2.0,
        expected_tomorrow_kwh=None,
        expected_day_after_kwh=None,
        peak_power_w=1000.0,
        peak_time=None,
        lower_today_kwh=4.0,
        upper_today_kwh=6.0,
        confidence=0.3,
        confidence_label="Low",
        radiation_confidence="LOW",
        hourly=(),
        physical_today_kwh=4.5,
        learned_correction_pct=0.0,
        weather_source="open-meteo",
    )
    forecast = compose_solar_forecast(_site(), intel, ())
    assert forecast.quality == "LOW"


def test_compose_solar_forecast_normalizes_intelligence_confidence_scale():
    """Intelligence engine emits 0–100; v2 contract expects 0–1."""
    ts = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    intel = IntelligenceForecast(
        site_id=1,
        generated_at=ts,
        model_version=INTELLIGENCE_MODEL_VERSION,
        status=ForecastStatus.HEALTHY,
        expected_today_kwh=14.0,
        remaining_today_kwh=6.0,
        expected_tomorrow_kwh=10.0,
        expected_day_after_kwh=None,
        peak_power_w=3000.0,
        peak_time=ts,
        lower_today_kwh=12.0,
        upper_today_kwh=16.0,
        confidence=58.0,
        confidence_label="Low",
        radiation_confidence="HIGH",
        hourly=(
            HourlyForecastPoint(
                timestamp=ts,
                physical_w=2000.0,
                corrected_w=2200.0,
                lower_w=1800.0,
                upper_w=2400.0,
                confidence=80.0,
            ),
        ),
        physical_today_kwh=13.0,
        learned_correction_pct=0.0,
        weather_source="smhi-strang",
    )
    forecast = compose_solar_forecast(_site(), intel, ())
    assert forecast.confidence == pytest.approx(0.58)
    assert forecast.quality == "MEDIUM"
    assert forecast.points[0].confidence == pytest.approx(0.8)


def test_compose_solar_forecast_high_confidence_not_inflated_to_high_when_degraded():
    ts = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
    intel = IntelligenceForecast(
        site_id=1,
        generated_at=ts,
        model_version=INTELLIGENCE_MODEL_VERSION,
        status=ForecastStatus.DEGRADED,
        expected_today_kwh=5.0,
        remaining_today_kwh=2.0,
        expected_tomorrow_kwh=None,
        expected_day_after_kwh=None,
        peak_power_w=1000.0,
        peak_time=None,
        lower_today_kwh=4.0,
        upper_today_kwh=6.0,
        confidence=30.0,
        confidence_label="Low",
        radiation_confidence="LOW",
        hourly=(),
        physical_today_kwh=4.5,
        learned_correction_pct=0.0,
        weather_source="open-meteo",
    )
    forecast = compose_solar_forecast(_site(), intel, ())
    assert forecast.confidence == pytest.approx(0.3)
    assert forecast.quality == "LOW"
