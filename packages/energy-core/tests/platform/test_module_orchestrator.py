"""ModuleOrchestrator lifecycle tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.capabilities.registry import CapabilityRegistry
from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.handlers import register_default_module_handlers
from energy_core.platform.modules.orchestrator import ModuleOrchestrator
from energy_core.platform.modules.runtime_registry import ModuleRuntimeRegistry
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.platform.modules.types import RuntimeStatus
from energy_core.seed import seed_sites


@pytest.fixture
async def orchestrator_context(tmp_path):
    register_default_modules()
    register_default_module_handlers()
    db_file = tmp_path / "orchestrator.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        module_gate_enabled=True,
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
async def test_start_module_idempotent(orchestrator_context):
    orchestrator, session_factory, site_id, runtime_registry, _, _ = orchestrator_context
    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    for _ in range(3):
        async with session_factory() as session:
            orchestrator._session = session
            await orchestrator.start_module(site_id, "feature.solar-forecast")
            await session.commit()

    assert runtime_registry.get_state(site_id, "feature.solar-forecast") == RuntimeStatus.RUNNING
    assert runtime_registry.worker_count(site_id, "feature.solar-forecast") == 1


@pytest.mark.asyncio
async def test_stop_module_idempotent(orchestrator_context):
    orchestrator, session_factory, site_id, runtime_registry, _, _ = orchestrator_context
    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.start_module(site_id, "feature.solar-forecast")
        await session.commit()

    for _ in range(3):
        async with session_factory() as session:
            orchestrator._session = session
            await orchestrator.stop_module(site_id, "feature.solar-forecast")
            await session.commit()

    assert runtime_registry.get_state(site_id, "feature.solar-forecast") == RuntimeStatus.STOPPED


@pytest.mark.asyncio
async def test_stop_unregisters_capabilities(orchestrator_context):
    orchestrator, session_factory, site_id, runtime_registry, capability_registry, _ = orchestrator_context
    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.start_module(site_id, "feature.solar-forecast")
        await session.commit()

    assert capability_registry.site_has_capability(site_id, Capability.FORECAST_SOLAR)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.stop_module(site_id, "feature.solar-forecast")
        await session.commit()

    assert not capability_registry.site_has_capability(site_id, Capability.FORECAST_SOLAR)
    assert runtime_registry.get_state(site_id, "feature.solar-forecast") == RuntimeStatus.STOPPED


@pytest.mark.asyncio
async def test_sync_site_starts_enabled_modules(orchestrator_context):
    orchestrator, session_factory, site_id, runtime_registry, _, _ = orchestrator_context
    async with session_factory() as session:
        resolver = SiteModuleResolver(session, settings=orchestrator._settings)
        await resolver.persist_enabled_override(site_id, "feature.solar-forecast", True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.sync_site(site_id)
        await session.commit()

    assert runtime_registry.get_state(site_id, "feature.solar-forecast") == RuntimeStatus.RUNNING


@pytest.mark.asyncio
async def test_dependency_reaction_blocks_smart_charging_when_chargeamps_stopped(orchestrator_context):
    orchestrator, session_factory, site_id, runtime_registry, capability_registry, settings = orchestrator_context
    from energy_core.platform.capabilities.types import Capability

    async with session_factory() as session:
        resolver = SiteModuleResolver(
            session,
            settings=settings,
            capability_registry=capability_registry,
            runtime_registry=runtime_registry,
        )
        await resolver.persist_enabled_override(site_id, "integration.chargeamps", True)
        await resolver.persist_enabled_override(site_id, "feature.smart-charging", True)
        await session.commit()
        invalidate_site_module_cache(site_id)

    capability_registry.register_provider(
        site_id=site_id,
        module_id="integration.chargeamps",
        capability=Capability.EV_CHARGER_START,
    )
    capability_registry.register_provider(
        site_id=site_id,
        module_id="integration.chargeamps",
        capability=Capability.EV_CHARGER_STOP,
    )
    runtime_registry.mark_running(site_id, "integration.chargeamps")
    runtime_registry.mark_running(site_id, "feature.smart-charging")

    async with session_factory() as session:
        orchestrator._session = session
        await orchestrator.stop_module(site_id, "integration.chargeamps")
        await session.commit()

    smart_state = runtime_registry.get_state(site_id, "feature.smart-charging")
    assert smart_state in {RuntimeStatus.STOPPED, RuntimeStatus.BLOCKED}
