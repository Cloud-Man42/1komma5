"""Tests for solar forecast engine integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.solar_forecast.engine import SolarForecastEngine
from energy_core.solar_forecast.types import (
    SitePerformanceProfile,
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
