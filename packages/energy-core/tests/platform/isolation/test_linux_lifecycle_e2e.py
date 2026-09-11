"""Linux lifecycle E2E tests (F-RV-03)."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.supervisor import RuntimeSupervisor
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages

from isolation_linux_helpers import cleanup_sandbox_env


async def _start_with_env(session, settings, session_factory, *, mode: str) -> tuple[IsolatedModuleRuntimeManager, str]:
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    os.environ["EMIC_SANDBOX_MODE"] = mode
    manager = IsolatedModuleRuntimeManager(session, settings)
    result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
    assert result.ok, result.message
    return manager, result.runtime_instance_id


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux lifecycle E2E requires bwrap")
@pytest.mark.asyncio
async def test_heartbeat_linux_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(
        update={
            "isolated_runtime_sandbox": "bwrap",
            "isolated_runtime_heartbeat_interval_seconds": 0.5,
            "isolated_runtime_heartbeat_miss_threshold": 1,
        }
    )
    os.environ["EMIC_SANDBOX_SKIP_HEARTBEAT"] = "1"
    manager, runtime_id = await _start_with_env(session, settings, session_factory, mode="benign")
    try:
        await asyncio.sleep(1.5)
        await RuntimeSupervisor(settings).supervise(manager)
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.state in {IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.PREPARING}
    finally:
        if manager.active_process(runtime_id) is not None:
            await manager.stop_runtime(runtime_id, reason="test cleanup")
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux lifecycle E2E requires bwrap")
@pytest.mark.asyncio
async def test_hung_runtime_linux_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(
        update={
            "isolated_runtime_sandbox": "bwrap",
            "isolated_runtime_heartbeat_interval_seconds": 0.5,
            "isolated_runtime_heartbeat_miss_threshold": 1,
        }
    )
    os.environ["EMIC_SANDBOX_SKIP_HEARTBEAT"] = "1"
    manager, runtime_id = await _start_with_env(session, settings, session_factory, mode="evil_hang")
    try:
        await asyncio.sleep(1.5)
        await RuntimeSupervisor(settings).supervise(manager)
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.state in {IsolatedRuntimeState.STOPPED, IsolatedRuntimeState.CRASHED, IsolatedRuntimeState.PREPARING}
        assert not manager.gateway.session_store.has_active_session(runtime_id)
    finally:
        if manager.active_process(runtime_id) is not None:
            await manager.stop_runtime(runtime_id, reason="test cleanup")
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux lifecycle E2E requires bwrap")
@pytest.mark.asyncio
async def test_crash_loop_quarantine_linux_e2e(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(
        update={
            "isolated_runtime_sandbox": "bwrap",
            "isolated_runtime_max_restarts": 1,
            "isolated_runtime_restart_backoff_seconds": 0.1,
        }
    )
    manager, runtime_id = await _start_with_env(session, settings, session_factory, mode="evil_crash")
    try:
        for _ in range(8):
            await manager.supervise_tick()
            await asyncio.sleep(0.25)
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.state == IsolatedRuntimeState.QUARANTINED
    finally:
        if manager.active_process(runtime_id) is not None:
            await manager.stop_runtime(runtime_id, reason="test cleanup")
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux lifecycle E2E requires bwrap")
@pytest.mark.asyncio
async def test_old_session_token_rejected_after_restart(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(
        update={
            "isolated_runtime_sandbox": "bwrap",
            "isolated_runtime_max_restarts": 2,
            "isolated_runtime_restart_backoff_seconds": 0.1,
        }
    )
    manager, runtime_id = await _start_with_env(session, settings, session_factory, mode="evil_crash")
    old_tokens = [
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    ]
    assert old_tokens
    old_token = old_tokens[0]
    try:
        await manager.supervise_tick()
        await asyncio.sleep(0.5)
        await manager.supervise_tick()
        assert manager.gateway.session_store.validate_session(
            old_token,
            runtime_instance_id=runtime_id,
            module_id="integration.sandbox-demo",
            site_id=1,
        ) is None
    finally:
        if manager.active_process(runtime_id) is not None:
            await manager.stop_runtime(runtime_id, reason="test cleanup")
        cleanup_sandbox_env()
