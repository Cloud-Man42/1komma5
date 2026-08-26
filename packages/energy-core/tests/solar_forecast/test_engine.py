"""Tests for solar forecast engine integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.solar_forecast.engine import SolarForecastEngine
from energy_core.solar_forecast.types import (
    ModelState,
    SitePerformanceProfile,
    SolarForecastModelProfile,
    SolarSiteConfiguration,
    WeatherForecast,
    WeatherForecastPoint,
)


def test_cold_start_produces_forecast() -> None:
    now = datetime(2026, 6, 15, 6, 0, tzinfo=UTC)
    site = SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.0,
        installed_peak_power_kw=8.0,
        enabled=True,
        timezone="Europe/Stockholm",
    )
    points = tuple(
        WeatherForecastPoint(
            timestamp=now + timedelta(minutes=15 * i),
            gti_wm2=500.0 if 8 <= (now + timedelta(minutes=15 * i)).hour <= 18 else 0.0,
            temperature_c=20.0,
            cloud_cover_pct=20.0,
        )
        for i in range(48)
    )
    weather = WeatherForecast(site_id=1, fetched_at=now, provider="test", points=points)
    profile = SitePerformanceProfile(site_id=1, sample_count=0)
    forecast = SolarForecastEngine().generate(site, weather, profile, now=now)
    assert forecast.expected_today_kwh >= 0
    assert forecast.quality in {"INSUFFICIENT_DATA", "LOW", "MEDIUM"}
    assert len(forecast.points) > 0


def test_no_data_model_uses_baseline_not_profile_correction() -> None:
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    site = SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.0,
        installed_peak_power_kw=9.0,
        inverter_max_power_kw=10.0,
        enabled=True,
        timezone="Europe/Stockholm",
    )
    weather_points = tuple(
        WeatherForecastPoint(
            timestamp=now - timedelta(hours=2) + timedelta(minutes=15 * i),
            ghi_wm2=700.0,
            gti_wm2=650.0,
            temperature_c=22.0,
            cloud_cover_pct=10.0,
        )
        for i in range(16)
    )
    weather = WeatherForecast(site_id=1, fetched_at=now, provider="test", points=weather_points)
    profile = SitePerformanceProfile(site_id=1, global_factor=0.5, sample_count=20)
    model_profile = SolarForecastModelProfile(
        site_id=1,
        model_state=ModelState.NO_DATA,
        historical_samples=0,
        correction_factor=1.0,
    )
    forecast = SolarForecastEngine().generate(
        site,
        weather,
        profile,
        now=now,
        model_profile=model_profile,
    )
    sample = next(p for p in forecast.points if p.corrected_power_w > 0)
    assert sample.correction_factor == 1.0
    assert sample.corrected_power_w == sample.baseline_power_w


def test_expected_today_includes_elapsed_day_intervals() -> None:
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    site = SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.0,
        installed_peak_power_kw=9.0,
        enabled=True,
        timezone="Europe/Stockholm",
    )
    weather_points = tuple(
        WeatherForecastPoint(
            timestamp=datetime(2026, 8, 26, 6, 0, tzinfo=UTC) + timedelta(minutes=15 * i),
            ghi_wm2=700.0,
            gti_wm2=650.0,
            temperature_c=22.0,
            cloud_cover_pct=10.0,
        )
        for i in range(32)
    )
    weather = WeatherForecast(site_id=1, fetched_at=now, provider="test", points=weather_points)
    profile = SitePerformanceProfile(site_id=1, sample_count=0)
    forecast = SolarForecastEngine().generate(site, weather, profile, now=now)
    assert forecast.expected_today_kwh > 0
    assert forecast.expected_today_kwh > forecast.remaining_today_kwh
