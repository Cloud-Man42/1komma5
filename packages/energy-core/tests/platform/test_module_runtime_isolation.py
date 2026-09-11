"""Two-site module runtime isolation tests."""

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
async def two_site_context(tmp_path):
    register_default_modules()
    register_default_module_handlers()
    db_file = tmp_path / "isolation.db"
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
        akarp = await SiteRepository(session).get_by_slug("akarp")
        denmark = await SiteRepository(session).get_by_slug("summer-house-denmark")
        assert akarp is not None
        assert denmark is not None
        resolver = SiteModuleResolver(session, settings=settings)
        await resolver.persist_enabled_override(akarp.id, "feature.solar-forecast", True)
        await resolver.persist_enabled_override(denmark.id, "feature.solar-forecast", False)
        await session.commit()
        invalidate_site_module_cache(akarp.id)
        invalidate_site_module_cache(denmark.id)

        orchestrator = ModuleOrchestrator(
            session,
            settings=settings,
            session_factory=session_factory,
            capability_registry=capability_registry,
            runtime_registry=runtime_registry,
        )
        await orchestrator.sync_site(akarp.id)
        await orchestrator.sync_site(denmark.id)
        await session.commit()
        yield akarp.id, denmark.id, runtime_registry, capability_registry
    await engine.dispose()


@pytest.mark.asyncio
async def test_two_site_runtime_isolation(two_site_context):
    akarp_id, denmark_id, runtime_registry, capability_registry = two_site_context
    assert runtime_registry.get_state(akarp_id, "feature.solar-forecast") == RuntimeStatus.RUNNING
    assert runtime_registry.get_state(denmark_id, "feature.solar-forecast") != RuntimeStatus.RUNNING
    assert runtime_registry.worker_count(akarp_id, "feature.solar-forecast") == 1
    assert runtime_registry.worker_count(denmark_id, "feature.solar-forecast") == 0
    from energy_core.platform.capabilities.types import Capability

    assert capability_registry.site_has_capability(akarp_id, Capability.FORECAST_SOLAR)
    assert not capability_registry.site_has_capability(denmark_id, Capability.FORECAST_SOLAR)
