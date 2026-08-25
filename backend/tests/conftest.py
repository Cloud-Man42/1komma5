"""Shared backend API test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint
from httpx import ASGITransport, AsyncClient


def _sample_weather(site_id: int = 1) -> WeatherForecast:
    now = datetime.now(UTC)
    points = tuple(
        WeatherForecastPoint(
            timestamp=now + timedelta(minutes=15 * i),
            ghi_wm2=600.0,
            gti_wm2=550.0,
            cloud_cover_pct=20.0,
            temperature_c=18.0,
        )
        for i in range(16)
    )
    return WeatherForecast(
        site_id=site_id,
        fetched_at=now,
        provider="test",
        points=points,
        source="live",
    )


@pytest.fixture(autouse=True)
def mock_open_meteo_forecast():
    """Prevent backend tests from calling the live Open-Meteo API."""
    with patch(
        "energy_core.solar_forecast.coordinator.OpenMeteoWeatherProvider.get_forecast",
        new=AsyncMock(side_effect=lambda site_config, *_args, **_kwargs: _sample_weather(site_config.site_id)),
    ):
        yield


@pytest.fixture(autouse=True)
def clear_dashboard_cache():
    """Every test gets a fresh database, so a cached section from an earlier test is stale."""
    from app.api.dashboard import _CACHE
    from app.widget_service import clear_snapshot_cache

    from app.widget_auth import WIDGET_RATE_LIMITER

    WIDGET_RATE_LIMITER._windows.clear()
    _CACHE.clear()
    clear_snapshot_cache()
    yield
    WIDGET_RATE_LIMITER._windows.clear()
    _CACHE.clear()
    clear_snapshot_cache()


@pytest.fixture
async def client(tmp_path):
    db_file = tmp_path / "test.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory, settings
    await engine.dispose()
