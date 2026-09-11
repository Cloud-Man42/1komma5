"""Integration tests for DB desired-state reconciliation after missed Redis events."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.capabilities.registry import CapabilityRegistry
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.handlers import register_default_module_handlers
from energy_core.platform.modules.orchestrator import ModuleOrchestrator
from energy_core.platform.modules.runtime_registry import ModuleRuntimeRegistry
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.platform.modules.types import RuntimeStatus
from energy_core.seed import seed_sites


@pytest.fixture
async def reconcile_context(tmp_path):
    register_default_modules()
    register_default_module_handlers()
    db_file = tmp_path / "reconcile.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        module_gate_enabled=True,
        redis_url="redis://127.0.0.1:6379/15",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()

    runtime_registry = ModuleRuntimeRegistry()
    capability_registry = CapabilityRegistry()

    async with session_factory() as session:
        orchestrator = ModuleOrchestrator(
            session,
            settings=settings,
            session_factory=session_factory,
            capability_registry=capability_registry,
            runtime_registry=runtime_registry,
        )
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        yield orchestrator, session_factory, site.id, runtime_registry, capability_registry, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_reconcile_stops_module_after_db_disable_without_event(reconcile_context):
    """Simulate missed Redis event: DB disabled while collector still running."""
    orchestrator, session_factory, site_id, runtime_registry, _, _ = reconcile_context
    module_id = "feature.solar-forecast"

    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, module_id, True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.start_module(site_id, module_id)
        await session.commit()

    assert runtime_registry.get_state(site_id, module_id) == RuntimeStatus.RUNNING

    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, module_id, False)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.reconcile_all_sites()
        await session.commit()

    assert runtime_registry.get_state(site_id, module_id) == RuntimeStatus.STOPPED


@pytest.mark.asyncio
async def test_reconcile_starts_module_after_db_enable_without_event(reconcile_context):
    """Simulate missed Redis event: DB enabled while collector still stopped."""
    orchestrator, session_factory, site_id, runtime_registry, _, _ = reconcile_context
    module_id = "feature.solar-forecast"

    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, module_id, False)
        await session.commit()
        invalidate_site_module_cache(site_id)

    assert runtime_registry.get_state(site_id, module_id) == RuntimeStatus.STOPPED

    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, module_id, True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.reconcile_all_sites()
        await session.commit()

    assert runtime_registry.get_state(site_id, module_id) == RuntimeStatus.RUNNING


@pytest.mark.asyncio
async def test_repeated_reconcile_is_idempotent(reconcile_context):
    orchestrator, session_factory, site_id, runtime_registry, _, _ = reconcile_context
    module_id = "feature.solar-forecast"

    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, module_id, True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    for _ in range(3):
        async with session_factory() as session:
            orchestrator._session = session
            await orchestrator.reconcile_all_sites()
            await session.commit()

    assert runtime_registry.get_state(site_id, module_id) == RuntimeStatus.RUNNING
    assert runtime_registry.worker_count(site_id, module_id) == 1
