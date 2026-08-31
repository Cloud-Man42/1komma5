"""Tests for extended multi-day forecast helper."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from energy_core.solar_forecast.extended_forecast import build_extended_forecast_points
from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecast, WeatherForecastPoint


def _site() -> SolarSiteConfiguration:
    return SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.2,
        installed_peak_power_kw=10.0,
        timezone="Europe/Stockholm",
        enabled=True,
    )


@pytest.mark.asyncio
async def test_build_extended_forecast_skips_covered_and_past_points():
    now = datetime(2026, 8, 29, 8, 0, tzinfo=UTC)
    covered_until = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
    future = datetime(2026, 9, 2, 10, 0, tzinfo=UTC)
    past = datetime(2026, 8, 28, 10, 0, tzinfo=UTC)

    provider = AsyncMock()
    provider.get_extended_hourly_forecast = AsyncMock(
        return_value=WeatherForecast(
            site_id=1,
            fetched_at=now,
            provider="open-meteo-extended",
            points=(
                WeatherForecastPoint(timestamp=past, gti_wm2=400.0),
                WeatherForecastPoint(timestamp=covered_until, gti_wm2=500.0),
                WeatherForecastPoint(timestamp=future, gti_wm2=600.0),
            ),
        )
    )

    points = await build_extended_forecast_points(
        _site(),
        provider,
        now=now,
        covered_until=covered_until,
        days=7,
    )

    assert len(points) == 1
    assert points[0].timestamp == future
    assert points[0].expected_energy_kwh > 0


@pytest.mark.asyncio
async def test_build_extended_forecast_returns_empty_when_days_zero():
    provider = AsyncMock()
    points = await build_extended_forecast_points(
        _site(),
        provider,
        now=datetime(2026, 8, 29, tzinfo=UTC),
        covered_until=datetime(2026, 8, 30, tzinfo=UTC),
        days=0,
    )
    assert points == ()
    provider.get_extended_hourly_forecast.assert_not_called()


@pytest.mark.asyncio
async def test_build_extended_forecast_swallows_provider_errors():
    provider = AsyncMock()
    provider.get_extended_hourly_forecast = AsyncMock(side_effect=RuntimeError("network"))

    points = await build_extended_forecast_points(
        _site(),
        provider,
        now=datetime(2026, 8, 29, tzinfo=UTC),
        covered_until=datetime(2026, 8, 30, tzinfo=UTC),
        days=7,
    )
    assert points == ()
