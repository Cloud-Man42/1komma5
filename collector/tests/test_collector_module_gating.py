"""Collector module runtime gating tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from collector.app.collector import Collector


@pytest.mark.asyncio
async def test_spa_integration_skips_sites_with_module_disabled():
    collector = Collector()
    collector._settings.arctic_spa_enabled = True
    collector._settings.module_gate_enabled = True
    collector._spa_polling.poll_due_consumers = AsyncMock(return_value=0)

    session = AsyncMock()
    site_repo = MagicMock()
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"

    with patch("energy_core.db.consumer_repo.ConsumerRepository") as consumer_repo_cls:
        consumer_repo_cls.return_value.list_enabled_spa_consumers = AsyncMock(
            return_value=[(MagicMock(), MagicMock(), site)]
        )
        with patch("energy_core.platform.modules.gating.is_module_runtime_active", AsyncMock(return_value=False)):
            with patch("energy_core.integrations.health.IntegrationHealthRecorder"):
                await collector._run_spa_integration(session, site_repo, {})

    collector._spa_polling.poll_due_consumers.assert_not_called()


@pytest.mark.asyncio
async def test_energy_balance_skips_sites_without_runtime():
    collector = Collector()
    collector._settings.module_gate_enabled = True

    session = AsyncMock()
    site_repo = MagicMock()
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"
    site_repo.list_all = AsyncMock(return_value=[site])

    with patch(
        "collector.app.collector.filter_sites_for_module",
        AsyncMock(return_value=[]),
    ):
        await collector._run_energy_balance(session, site_repo, {})


@pytest.mark.asyncio
async def test_vehicle_charge_sessions_skips_sites_without_runtime():
    collector = Collector()
    collector._settings.module_gate_enabled = True
    collector._vehicle_charge_sessions.process_site = AsyncMock(return_value=0)

    session = AsyncMock()
    site_repo = MagicMock()
    site = MagicMock()
    site.id = 1
    site.slug = "akarp"
    site_repo.list_all = AsyncMock(return_value=[site])

    with patch(
        "collector.app.collector.filter_sites_for_module",
        AsyncMock(return_value=[]),
    ):
        await collector._run_vehicle_charge_sessions(session, site_repo, {})

    collector._vehicle_charge_sessions.process_site.assert_not_called()


@pytest.mark.asyncio
async def test_fast_lane_skips_heartbeat_fetch_when_no_runtime_sites():
    collector = Collector()
    collector._settings.module_gate_enabled = True
    collector._snapshot_writer.write_sites = AsyncMock()
    collector._charging_engine.run_cycle = AsyncMock(return_value=0)
    collector._sync_dirty_module_sites = AsyncMock()

    session = AsyncMock()
    site_repo = MagicMock()
    site_repo.list_all = AsyncMock(return_value=[])
    collector._session_factory = MagicMock()
    collector._session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
    collector._session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("collector.app.collector.SiteRepository", return_value=site_repo):
        with patch(
            "collector.app.collector.any_site_module_runtime_active",
            AsyncMock(return_value=False),
        ):
            with patch("collector.app.collector.create_heartbeat_provider_from_db") as provider_factory:
                await collector.run_fast_lane()
                provider_factory.assert_not_called()
