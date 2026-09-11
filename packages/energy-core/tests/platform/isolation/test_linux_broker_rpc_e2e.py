"""Live broker RPC from Linux sandbox (F-RV-06)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.supervisor import RuntimeSupervisor
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeStartRequest
from energy_core.platform.modules.packages.loader import load_installed_module_packages

from isolation_linux_helpers import cleanup_sandbox_env, read_probes, start_runtime_with_mode


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Live broker RPC requires Linux bwrap")
@pytest.mark.asyncio
async def test_live_broker_rpc_from_sandbox(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    os.environ["EMIC_BROKER_ALLOW_URL"] = "https://example.com/"
    os.environ["EMIC_BROKER_OWN_SECRET"] = "own-test-secret"
    register_default_modules()
    await load_installed_module_packages(session_factory, settings=settings)
    os.environ["EMIC_SANDBOX_MODE"] = "probe_broker_live"
    manager = IsolatedModuleRuntimeManager(session, settings)
    original_register = manager.gateway.register_runtime

    def _register_with_broker_perms(record, *, permissions, capabilities):
        merged = tuple(set(permissions) | {"network.external", "secrets.read_own"})
        return original_register(record, permissions=merged, capabilities=capabilities)

    manager.gateway.register_runtime = _register_with_broker_perms
    manager.gateway.network_broker.allow_host(
        module_id="integration.sandbox-demo",
        site_id=1,
        host="example.com",
    )
    manager.gateway.secret_broker.register_secret(
        module_id="integration.sandbox-demo",
        site_id=1,
        secret_ref="own-test-secret",
        value="synthetic-test-value",
    )
    with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=httpx.Response(200, text="ok"))):
        result = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
    assert result.ok, result.message
    runtime_id = result.runtime_instance_id
    record = await manager.get_runtime(runtime_id)
    perms = json.loads(record.permissions_json or "[]")
    assert "network.external" in perms, f"missing network.external in {perms}"
    data_path = Path(record.data_path)
    try:
        probes = read_probes(data_path)
        assert probes["network_allow"] == "allowed"
        assert probes["network_deny"].startswith("denied")
        assert probes["secret_own"] == "allowed"
        assert probes["secret_enum"].startswith("denied")
        assert probes["read_own_site"] == "allowed"
        assert probes["read_cross_site"].startswith("denied")
        audit = manager.gateway.secret_broker._audit_log
        assert all("synthetic-test-value" not in str(entry) for entry in audit)
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Live broker RPC requires Linux bwrap")
@pytest.mark.asyncio
async def test_redirect_to_private_live_broker_path(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(session, settings, session_factory, mode="benign")
    manager.gateway.network_broker.allow_host(module_id="integration.sandbox-demo", site_id=1, host="example.com")
    token = next(
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    )
    redirect_response = httpx.Response(
        302,
        headers={"location": "https://127.0.0.1/internal"},
        request=httpx.Request("GET", "https://example.com/start"),
    )
    try:
        with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=redirect_response)):
            response = await manager.gateway._dispatch(
                1,
                "NetworkRequest",
                {
                    "runtime_instance_id": runtime_id,
                    "module_id": "integration.sandbox-demo",
                    "site_id": 1,
                    "url": "https://example.com/start",
                    "_session_token": token,
                },
            )
        assert b"error" in response.lower() or b"forbidden" in response.lower() or b"127" in response.lower()
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Live broker RPC requires Linux bwrap")
@pytest.mark.asyncio
async def test_disk_quota_linux(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(
        update={"isolated_runtime_sandbox": "bwrap", "isolated_runtime_data_quota_mb": 1}
    )
    manager, runtime_id, data_path = await start_runtime_with_mode(session, settings, session_factory, mode="probe_disk")
    try:
        probes = read_probes(data_path)
        await RuntimeSupervisor(settings).supervise(manager)
        record = await manager.get_runtime(runtime_id)
        assert record is not None
        assert record.state in {
            IsolatedRuntimeState.QUARANTINED,
            IsolatedRuntimeState.STOPPED,
            IsolatedRuntimeState.CRASHED,
        } or probes["disk"].startswith("stopped:")
    finally:
        proc = manager.active_process(runtime_id)
        if proc is not None:
            await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Live broker RPC requires Linux bwrap")
@pytest.mark.asyncio
async def test_oversized_rpc_rejected(sandbox_demo_package):
    session, settings, session_factory = sandbox_demo_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(session, settings, session_factory, mode="benign")
    manager._gateway._settings = settings.model_copy(update={"isolated_runtime_rpc_max_bytes": 256})
    token = next(
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    )
    try:
        response = await manager.gateway._dispatch(
            1,
            "NetworkRequest",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.sandbox-demo",
                "site_id": 1,
                "url": "https://example.com/",
                "_session_token": token,
            },
        )
        assert b"error" in response.lower() or b"denied" in response.lower() or b"allowlisted" in response.lower()
    finally:
        proc = manager.active_process(runtime_id)
        if proc is not None:
            await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()
