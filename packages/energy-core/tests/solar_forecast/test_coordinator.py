"""Tests for SolarForecastCoordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository
from energy_core.solar_forecast.constants import diurnal_solar_factor
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint


@pytest.fixture
async def sqlite_session():
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        solar_forecast_refresh_minutes=5,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings
    await engine.dispose()


def test_diurnal_is_zero_outside_daylight():
    assert diurnal_solar_factor(3) == 0.0
    assert diurnal_solar_factor(22) == 0.0
    assert diurnal_solar_factor(13) > 0.9


def test_fallback_weather_generates_points():
    coord = SolarForecastCoordinator(
        Settings(_env_file=None, APP_ENV="test", solar_forecast_horizon_hours=24)
    )
    site = SimpleNamespace(site_id=1)
    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    weather = coord._fallback_weather(site, now)
    assert weather.source == "fallback"
    assert len(weather.points) == 24 * 4
    assert weather.points[0].ghi_wm2 >= 0


@pytest.mark.asyncio
async def test_refresh_site_now_skips_disabled_config(sqlite_session):
    session, settings = sqlite_session
    from energy_core.db.repositories import SiteRepository

    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    await session.commit()

    coord = SolarForecastCoordinator(settings)
    refreshed = await coord.refresh_site_now(session, site)
    assert refreshed is False


@pytest.mark.asyncio
async def test_refresh_site_now_generates_forecast_when_enabled(sqlite_session):
    session, settings = sqlite_session
    from energy_core.db.repositories import SiteRepository

    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    config_repo = SolarSiteConfigRepository(session)
    await config_repo.upsert(
        site.id,
        latitude=55.60,
        longitude=13.00,
        installed_peak_power_kw=8.0,
        azimuth_deg=180,
        tilt_deg=30,
        enabled=True,
    )
    await session.commit()

    now = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)
    weather = WeatherForecast(
        site_id=site.id,
        fetched_at=now,
        provider="test",
        source="live",
        points=tuple(
            WeatherForecastPoint(
                timestamp=now + timedelta(minutes=15 * i),
                ghi_wm2=600.0,
                gti_wm2=550.0,
                cloud_cover_pct=10.0,
                temperature_c=20.0,
            )
            for i in range(16)
        ),
    )

    coord = SolarForecastCoordinator(settings)
    with patch.object(
        coord,
        "_fetch_weather",
        new=AsyncMock(return_value=(weather, "live", 0.0)),
    ):
        refreshed = await coord.refresh_site_now(session, site)

    assert refreshed is True

    from energy_core.db.solar_forecast_repo import SolarForecastRepository

    latest = await SolarForecastRepository(session).get_latest(site.id)
    assert latest is not None
    assert latest.expected_today_kwh >= 0
