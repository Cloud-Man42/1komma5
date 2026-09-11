"""Step 2.5 acceptance tests for solar-forecast and smart-charging gating."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collector.app.collector import Collector
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.runtime_registry import ModuleRuntimeRegistry
from energy_core.platform.modules.types import RuntimeStatus
from energy_core.seed import seed_sites


@pytest.fixture
async def collector_session(tmp_path):
    register_default_modules()
    db_file = tmp_path / "acceptance.db"
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
    yield session_factory, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_solar_forecast_skipped_when_runtime_stopped(collector_session):
    session_factory, settings = collector_session
    collector = Collector()
    collector._settings = settings
    collector._solar_forecast.evaluate_site_observations = AsyncMock()
    collector._solar_forecast.run_due_sites = AsyncMock(return_value=0)

    async with session_factory() as session:
        site_repo = SiteRepository(session)
        await collector._run_solar_forecast(session, site_repo)

    collector._solar_forecast.evaluate_site_observations.assert_not_called()


@pytest.mark.asyncio
async def test_solar_forecast_runs_when_runtime_active(collector_session):
    session_factory, settings = collector_session
    runtime_registry = ModuleRuntimeRegistry()
    collector = Collector()
    collector._settings = settings
    collector._solar_forecast.evaluate_site_observations = AsyncMock()
    collector._solar_forecast.run_due_sites = AsyncMock(return_value=1)

    async with session_factory() as session:
        from energy_core.platform.modules.site_modules import SiteModuleResolver

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        resolver = SiteModuleResolver(session, settings=settings)
        await resolver.persist_enabled_override(site.id, "feature.solar-forecast", True)
        await session.commit()
        runtime_registry.mark_running(site.id, "feature.solar-forecast")
        site_repo = SiteRepository(session)
        with patch(
            "energy_core.platform.modules.gating.default_module_runtime_registry",
            runtime_registry,
        ):
            with patch("energy_core.integrations.health.IntegrationHealthRecorder"):
                with patch("energy_core.integrations.collector_health.record_provider_outcome", AsyncMock()):
                    await collector._run_solar_forecast(session, site_repo)

    collector._solar_forecast.evaluate_site_observations.assert_called()
    assert collector._solar_forecast.evaluate_site_observations.call_count >= 1


@pytest.mark.asyncio
async def test_solar_forecast_enable_disable_loop_stable_worker_count(collector_session):
    session_factory, settings = collector_session
    runtime_registry = ModuleRuntimeRegistry()

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        for _ in range(5):
            runtime_registry.mark_running(site.id, "feature.solar-forecast")
            assert runtime_registry.worker_count(site.id, "feature.solar-forecast") == 1
            runtime_registry.mark_stopped(site.id, "feature.solar-forecast")
            assert runtime_registry.worker_count(site.id, "feature.solar-forecast") == 0


@pytest.mark.asyncio
async def test_smart_charging_engine_skips_when_runtime_inactive():
    from datetime import UTC, datetime

    from energy_core.charging.engine import SmartChargingEngine
    from energy_core.db.models import EvChargerModel

    engine = SmartChargingEngine()
    session = AsyncMock()
    charger = EvChargerModel(
        id=1,
        site_id=1,
        name="Halo",
        manufacturer="ChargeAmps",
        model="Halo",
        control_source="chargeamp",
        bridge_enabled=True,
        chargeamp_charger_id="halo-1",
        charging_mode="SMART_CHARGE",
    )
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"
    site.external_system_id = "sys-1"

    with patch("energy_core.config.get_settings") as get_settings:
        get_settings.return_value = Settings(_env_file=None, APP_ENV="test", module_gate_enabled=True)
        with patch(
            "energy_core.platform.modules.gating.is_module_runtime_active",
            AsyncMock(return_value=False),
        ):
            with patch("energy_core.charging.engine.evaluate_smart_charging") as evaluate:
                await engine._run_charger_cycle(session, charger, site, now=datetime.now(UTC))
                evaluate.assert_not_called()
