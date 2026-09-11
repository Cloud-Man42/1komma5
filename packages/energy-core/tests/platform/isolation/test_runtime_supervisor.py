"""Runtime supervisor unit tests (F-10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.isolation.supervisor import RuntimeSupervisor
from energy_core.platform.modules.isolation.types import IsolatedRuntimeRecord, IsolatedRuntimeState


def _record(**overrides) -> IsolatedRuntimeRecord:
    base = dict(
        id=1,
        runtime_instance_id="rt-1",
        module_id="mod-a",
        version="1.0.0",
        publisher_id="pub-a",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.RUNNING,
        process_identity="uid:10001",
        process_pid=123,
        sandbox_mode="subprocess",
        socket_path="/tmp/rt.sock",
        package_path="/pkg",
        data_path="/data",
        protocol_version=1,
        restart_count=0,
        last_error=None,
        reason_codes=(),
        permissions_json="[]",
        started_at=datetime.now(UTC) - timedelta(seconds=120),
        last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=120),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    base.update(overrides)
    return IsolatedRuntimeRecord(**base)


@pytest.mark.asyncio
async def test_heartbeat_timeout_stops_runtime():
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_HEARTBEAT_INTERVAL_SECONDS=1.0,
        ISOLATED_RUNTIME_HEARTBEAT_MISS_THRESHOLD=1,
    )
    supervisor = RuntimeSupervisor(settings)
    manager = MagicMock()
    manager.list_runtimes = AsyncMock(return_value=[_record()])
    manager.active_process.return_value = None
    manager.get_runtime = AsyncMock(return_value=_record(state=IsolatedRuntimeState.STOPPED))
    manager.stop_runtime = AsyncMock()
    manager._repo = MagicMock()
    manager._repo.transition = AsyncMock()
    manager._audit = AsyncMock()

    await supervisor.supervise(manager)
    assert manager.stop_runtime.await_count >= 1


@pytest.mark.asyncio
async def test_crash_loop_quarantine():
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_MAX_RESTARTS=2,
        ISOLATED_RUNTIME_RESTART_BACKOFF_SECONDS=0.5,
    )
    supervisor = RuntimeSupervisor(settings)
    manager = MagicMock()
    manager._repo = MagicMock()
    manager._repo.transition = AsyncMock()
    manager._audit = AsyncMock()
    record = _record(restart_count=2, state=IsolatedRuntimeState.CRASHED)
    await supervisor._maybe_restart(manager, record, reason="crash")
    manager._repo.transition.assert_awaited()
    _args, kwargs = manager._repo.transition.await_args
    assert kwargs["to_state"] == IsolatedRuntimeState.QUARANTINED
