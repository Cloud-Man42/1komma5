"""RuntimeSecurityMonitor unit tests (F-RV-07)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.governance.types import RevocationMatch
from energy_core.platform.modules.isolation.security_monitor import RuntimeSecurityMonitor
from energy_core.platform.modules.isolation.types import IsolatedRuntimeRecord, IsolatedRuntimeState, RuntimeEventType
from energy_core.platform.modules.marketplace.types import MetadataHealth
from datetime import UTC, datetime


def _record(**overrides) -> IsolatedRuntimeRecord:
    base = dict(
        id=1,
        runtime_instance_id="rt-1",
        module_id="integration.sandbox-demo",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.RUNNING,
        process_identity="uid:10001",
        process_pid=123,
        sandbox_mode="bwrap",
        socket_path="/tmp/rt.sock",
        package_path="/pkg",
        data_path="/data",
        protocol_version=1,
        restart_count=0,
        last_error=None,
        reason_codes=(),
        permissions_json="[]",
        started_at=datetime.now(UTC),
        last_heartbeat_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(overrides)
    return IsolatedRuntimeRecord(**base)


@pytest.fixture
def monitor(isolation_session):
    session, settings, _ = isolation_session
    settings = settings.model_copy(update={"marketplace_metadata_enabled": True})
    return RuntimeSecurityMonitor(session, settings), session, settings


@pytest.mark.asyncio
async def test_publisher_revocation_stops_runtime(monitor):
    mon, session, settings = monitor
    manager = MagicMock()
    manager.get_runtime = AsyncMock(return_value=_record())
    manager.list_runtimes = AsyncMock(return_value=[_record()])
    manager.stop_runtime = AsyncMock()
    manager._repo = MagicMock()
    manager._repo.transition = AsyncMock()
    manager._audit = AsyncMock()

    mon._revocations.load_context = AsyncMock(
        return_value=MagicMock(
            metadata_health=MetadataHealth.HEALTHY.value,
            revocations=(
                RevocationMatch(
                    revocation_id="rev-1",
                    severity="HIGH",
                    scope="publisher",
                    publisher_id="emic-tests",
                    module_id=None,
                ),
            ),
        )
    )
    mon._revocations.find_active_revocation = MagicMock(
        return_value=RevocationMatch(
            revocation_id="rev-1",
            severity="HIGH",
            scope="publisher",
            publisher_id="emic-tests",
            module_id=None,
        )
    )

    stopped = await mon.check_runtime(manager, "rt-1")
    assert stopped is True
    manager.stop_runtime.assert_awaited_once()
    manager._repo.transition.assert_awaited()
    manager._audit.assert_awaited()
    assert manager._audit.await_args.kwargs["event_type"] == RuntimeEventType.REVOCATION_STOP


@pytest.mark.asyncio
async def test_module_revocation_stops_runtime(monitor):
    mon, _, _ = monitor
    manager = MagicMock()
    manager.get_runtime = AsyncMock(return_value=_record())
    manager.stop_runtime = AsyncMock()
    manager._repo = MagicMock()
    manager._repo.transition = AsyncMock()
    manager._audit = AsyncMock()
    mon._revocations.load_context = AsyncMock(
        return_value=MagicMock(metadata_health=MetadataHealth.HEALTHY.value, revocations=())
    )
    mon._revocations.find_active_revocation = MagicMock(
        return_value=RevocationMatch(
            revocation_id="rev-2",
            severity="HIGH",
            scope="module",
            publisher_id=None,
            module_id="integration.sandbox-demo",
        )
    )
    assert await mon.check_runtime(manager, "rt-1") is True


@pytest.mark.asyncio
async def test_critical_advisory_stops_runtime(monitor):
    mon, _, settings = monitor
    manager = MagicMock()
    manager.get_runtime = AsyncMock(return_value=_record())
    manager.stop_runtime = AsyncMock()
    manager._repo = MagicMock()
    manager._repo.transition = AsyncMock()
    manager._audit = AsyncMock()
    mon._revocations.load_context = AsyncMock(
        return_value=MagicMock(metadata_health=MetadataHealth.HEALTHY.value, revocations=())
    )
    mon._revocations.find_active_revocation = MagicMock(return_value=None)
    mon._trust_cache.get_or_create = AsyncMock(return_value=MagicMock())
    mon._trust_cache.parse_advisories = MagicMock(
        return_value={
            "bundle": {"generation": 1, "generated_at": "2026-09-08T12:00:00Z"},
            "advisories": [
                {
                    "advisory_id": "adv-crit",
                    "severity": "CRITICAL",
                    "status": "ACTIVE",
                    "affected": {
                        "purl": "pkg:emic/integration.sandbox-demo@1.0.0",
                        "version_range": ">=1.0.0",
                    },
                }
            ],
        }
    )
    assert await mon.check_runtime(manager, "rt-1") is True
    manager.stop_runtime.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_match_leaves_runtime(monitor):
    mon, _, _ = monitor
    manager = MagicMock()
    manager.get_runtime = AsyncMock(return_value=_record())
    mon._revocations.load_context = AsyncMock(
        return_value=MagicMock(metadata_health=MetadataHealth.HEALTHY.value, revocations=())
    )
    mon._revocations.find_active_revocation = MagicMock(return_value=None)
    mon._trust_cache.get_or_create = AsyncMock(return_value=MagicMock())
    mon._trust_cache.parse_advisories = MagicMock(return_value=None)
    assert await mon.check_runtime(manager, "rt-1") is False


@pytest.mark.asyncio
async def test_already_stopped_runtime_ignored(monitor):
    mon, _, _ = monitor
    manager = MagicMock()
    manager.get_runtime = AsyncMock(return_value=_record(state=IsolatedRuntimeState.STOPPED))
    assert await mon.check_runtime(manager, "rt-1") is False


@pytest.mark.asyncio
async def test_scan_active_stops_multiple(monitor):
    mon, _, _ = monitor
    manager = MagicMock()
    manager.list_runtimes = AsyncMock(
        return_value=[_record(runtime_instance_id="rt-1"), _record(runtime_instance_id="rt-2")]
    )
    mon.check_runtime = AsyncMock(side_effect=[True, False])
    stopped = await mon.scan_active(manager)
    assert stopped == 1
