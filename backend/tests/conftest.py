"""Shared backend API test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.auth.passwords import hash_password
from energy_core.auth.repos.user_repo import RoleRepository, UserRepository
from energy_core.auth.seed_rbac import ensure_rbac_seed
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
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
            weather_code=1,
            wind_speed_ms=3.1,
            relative_humidity_pct=52.0,
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
    from app.dashboard_compute import _CACHE
    from app.widget_service import clear_snapshot_cache
    from energy_core.cache.service import reset_cache_service

    from app.login_rate_limit import LOGIN_RATE_LIMITER
    from app.tenant_rate_limit import TENANT_API_RATE_LIMITER
    from app.widget_auth import WIDGET_RATE_LIMITER

    LOGIN_RATE_LIMITER._windows.clear()
    TENANT_API_RATE_LIMITER.clear()
    WIDGET_RATE_LIMITER._windows.clear()
    _CACHE.clear()
    reset_cache_service()
    clear_snapshot_cache()
    yield
    LOGIN_RATE_LIMITER._windows.clear()
    TENANT_API_RATE_LIMITER.clear()
    WIDGET_RATE_LIMITER._windows.clear()
    _CACHE.clear()
    reset_cache_service()
    clear_snapshot_cache()


@pytest.fixture(autouse=True)
def isolate_admin_token_env(monkeypatch):
    """Tests expect open admin routes unless a fixture sets EMIC_ADMIN_TOKEN explicitly."""
    monkeypatch.delenv("EMIC_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("EMIC_ADMIN_TOKEN", "")


@pytest.fixture(autouse=True)
def restore_module_registry():
    """Package loader tests mutate the process-global registry; reset for each backend test."""
    from energy_core.platform.modules.bootstrap import register_default_modules
    from energy_core.platform.modules.registry import default_module_registry
    from energy_core.platform.modules.site_modules import invalidate_site_module_cache

    default_module_registry.clear()
    register_default_modules()
    invalidate_site_module_cache()
    yield
    default_module_registry.clear()
    register_default_modules()
    invalidate_site_module_cache()


@pytest.fixture
async def client(tmp_path):
    db_file = tmp_path / "test.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        emic_admin_token="",
        emic_user_auth_enabled=False,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        from energy_core.auth.seed_rbac import ensure_rbac_seed

        await ensure_rbac_seed(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory, settings
    await engine.dispose()


@pytest.fixture
async def auth_client(tmp_path):
    """Authenticated API client with seeded RBAC users (admin, viewer, operator)."""
    db_file = tmp_path / "auth-test.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        emic_admin_token="break-glass-secret",
        emic_user_auth_enabled=True,
        emic_cookie_secure=False,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await ensure_rbac_seed(session)
        user_repo = UserRepository(session)
        viewer_role = await RoleRepository(session).get_by_name("VIEWER")
        operator_role = await RoleRepository(session).get_by_name("OPERATOR")
        super_role = await RoleRepository(session).get_by_name("SUPER_ADMIN")
        sites = await SiteRepository(session).list_all()
        akarp = next(s for s in sites if s.slug == "akarp")

        admin = await user_repo.create_user(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            display_name="Admin",
        )
        await user_repo.set_roles(admin.id, [super_role.id])
        await user_repo.set_site_access(admin.id, [s.id for s in sites])

        viewer = await user_repo.create_user(
            username="viewer",
            email="viewer@example.com",
            password_hash=hash_password("ViewerPass123!"),
            display_name="Viewer",
        )
        await user_repo.set_roles(viewer.id, [viewer_role.id])
        await user_repo.set_site_access(viewer.id, [akarp.id])

        operator = await user_repo.create_user(
            username="operator",
            email="operator@example.com",
            password_hash=hash_password("OperatorPass123!"),
            display_name="Operator",
        )
        await user_repo.set_roles(operator.id, [operator_role.id])
        await user_repo.set_site_access(operator.id, [akarp.id])

        disabled = await user_repo.create_user(
            username="disabled",
            email="disabled@example.com",
            password_hash=hash_password("DisabledPass123!"),
            display_name="Disabled",
            must_change_password=False,
        )
        disabled.is_active = False
        from energy_core.tenancy.sync import sync_tenant_memberships_for_default_tenant

        await sync_tenant_memberships_for_default_tenant(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, settings
    await engine.dispose()

