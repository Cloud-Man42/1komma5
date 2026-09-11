"""Site module projection and override tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.seed import seed_sites


@pytest.fixture
async def module_session(tmp_path):
    register_default_modules()
    db_file = tmp_path / "site-modules.db"
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
async def test_override_enable_wins_over_projection(module_session):
    session_factory, settings = module_session
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        resolver = SiteModuleResolver(session, settings=settings)
        before = await resolver.list_modules(site.id)
        solar_before = next(m for m in before if m.module_id == "feature.solar-forecast")
        await resolver.persist_enabled_override(site.id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site.id)
        after = await resolver.list_modules(site.id, use_cache=False)
        solar_after = next(m for m in after if m.module_id == "feature.solar-forecast")
        assert solar_after.enabled is True
        if not solar_before.enabled:
            assert solar_after.enabled != solar_before.enabled


@pytest.mark.asyncio
async def test_override_disable_wins_over_projection(module_session):
    session_factory, settings = module_session
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        resolver = SiteModuleResolver(session, settings=settings)
        await resolver.persist_enabled_override(site.id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site.id)
        await resolver.persist_enabled_override(site.id, "feature.solar-forecast", False)
        await session.commit()
        invalidate_site_module_cache(site.id)
        modules = await resolver.list_modules(site.id, use_cache=False)
        solar = next(m for m in modules if m.module_id == "feature.solar-forecast")
        assert solar.enabled is False


@pytest.mark.asyncio
async def test_list_modules_filters_legacy_alias_ids(module_session):
    session_factory, settings = module_session
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        resolver = SiteModuleResolver(session, settings=settings)
        module_ids = {m.module_id for m in await resolver.list_modules(site.id)}
        assert "charging" not in module_ids
        assert "vehicles" not in module_ids
        assert "feature.smart-charging" in module_ids or "integration.chargeamps" in module_ids
