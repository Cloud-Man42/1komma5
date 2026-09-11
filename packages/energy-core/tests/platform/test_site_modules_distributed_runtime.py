"""Site module API uses distributed runtime state from Redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from energy_core.cache.module_runtime_state import RuntimeStateSnapshot
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.solar_forecast_repo import SolarSiteConfigRepository
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.site_modules import SiteModuleResolver
from energy_core.platform.modules.types import RuntimeStatus
from energy_core.seed import seed_sites


@pytest.fixture
async def module_session(tmp_path):
    register_default_modules()
    db_file = tmp_path / "site-modules-distributed.db"
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
    yield session_factory, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_modules_uses_distributed_runtime_state(module_session):
    session_factory, settings = module_session
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        solar_repo = SolarSiteConfigRepository(session)
        config = await solar_repo.get(site.id, timezone=site.timezone)
        if config is None:
            pytest.skip("akarp solar config missing")

        distributed = {
            "feature.solar-forecast": RuntimeStateSnapshot(
                site_id=site.id,
                module_id="feature.solar-forecast",
                runtime_state=RuntimeStatus.RUNNING,
            )
        }
        with patch(
            "energy_core.platform.modules.site_modules.read_runtime_states",
            AsyncMock(return_value=distributed),
        ):
            resolver = SiteModuleResolver(session, settings=settings)
            modules = await resolver.list_modules(site.id, use_cache=False)
        solar = next(m for m in modules if m.module_id == "feature.solar-forecast")
        assert solar.runtime_status == RuntimeStatus.RUNNING


@pytest.mark.asyncio
async def test_distributed_running_not_overridden_to_blocked_when_deps_missing_locally(module_session):
    """Collector Redis RUNNING wins over backend-local missing capability projection."""
    session_factory, settings = module_session
    settings = Settings(**{**settings.model_dump(), "redis_url": "redis://127.0.0.1:6379/15"})
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        resolver = SiteModuleResolver(session, settings=settings)
        await resolver.persist_enabled_override(site.id, "feature.smart-charging", True)
        await session.commit()

        distributed = {
            "feature.smart-charging": RuntimeStateSnapshot(
                site_id=site.id,
                module_id="feature.smart-charging",
                runtime_state=RuntimeStatus.RUNNING,
            )
        }
        with patch(
            "energy_core.platform.modules.site_modules.read_runtime_states",
            AsyncMock(return_value=distributed),
        ):
            modules = await resolver.list_modules(site.id, use_cache=False)
        smart = next(m for m in modules if m.module_id == "feature.smart-charging")
        assert smart.runtime_status == RuntimeStatus.RUNNING
