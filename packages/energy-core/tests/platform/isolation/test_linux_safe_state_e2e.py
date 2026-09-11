"""Linux safe-state E2E tests (F-RV-05)."""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

from energy_core.platform.modules.isolation.types import IsolatedRuntimeState, RuntimeStartRequest

from isolation_linux_helpers import cleanup_sandbox_env, start_runtime_with_mode


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux safe-state E2E requires bwrap")
@pytest.mark.asyncio
async def test_control_lease_live_and_revoke_on_crash(runtime_e2e_package):
    session, settings, session_factory = runtime_e2e_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(
        session, settings, session_factory, mode="benign", module_id="integration.runtime-e2e"
    )
    broker = manager.gateway.device_broker
    broker.synthetic.register_device(site_id=1, device_id="dev-1", safe_default_power_w=0.0)
    try:
        lease = await manager.gateway._dispatch(
            1,
            "AcquireControlLease",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.runtime-e2e",
                "site_id": 1,
                "capability": "device.control",
                "params": {"device_id": "dev-1", "site_id": 1},
                "_session_token": next(
                    token
                    for token, sess in manager.gateway.session_store._sessions.items()
                    if sess.runtime_instance_id == runtime_id and not sess.revoked
                ),
            },
        )
        assert b"error" not in lease.lower()
        cmd = await manager.gateway._dispatch(
            2,
            "Command",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.runtime-e2e",
                "site_id": 1,
                "capability": "device.control",
                "command": "set_power",
                "params": {"device_id": "dev-1", "site_id": 1, "power_w": 5000},
                "_session_token": next(
                    token
                    for token, sess in manager.gateway.session_store._sessions.items()
                    if sess.runtime_instance_id == runtime_id and not sess.revoked
                ),
            },
        )
        assert b"error" not in cmd.lower()
        device = broker.synthetic.get(1, "dev-1")
        assert device is not None
        assert device.power_w == 5000
        await manager.stop_runtime(runtime_id, reason="simulated crash")
        assert device.power_w == 0.0
        assert device.owner_runtime_id is None
    finally:
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux safe-state E2E requires bwrap")
@pytest.mark.asyncio
async def test_dead_runtime_commands_denied(runtime_e2e_package):
    session, settings, session_factory = runtime_e2e_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(
        session, settings, session_factory, mode="benign", module_id="integration.runtime-e2e"
    )
    token = next(
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    )
    await manager.stop_runtime(runtime_id, reason="dead runtime test")
    response = await manager.gateway._dispatch(
        1,
        "Command",
        {
            "runtime_instance_id": runtime_id,
            "module_id": "integration.sandbox-demo",
            "site_id": 1,
            "capability": "device.control",
            "command": "set_power",
            "params": {"device_id": "dev-1", "site_id": 1, "power_w": 1000},
            "_session_token": token,
        },
    )
    assert b"error" in response.lower() or b"denied" in response.lower() or b"not running" in response.lower()
    cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux safe-state E2E requires bwrap")
@pytest.mark.asyncio
async def test_cross_site_control_denied(runtime_e2e_package):
    session, settings, session_factory = runtime_e2e_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(
        session, settings, session_factory, mode="benign", module_id="integration.runtime-e2e", site_id=1
    )
    broker = manager.gateway.device_broker
    broker.synthetic.register_device(site_id=2, device_id="dev-b", safe_default_power_w=0.0)
    token = next(
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    )
    try:
        response = await manager.gateway._dispatch(
            1,
            "AcquireControlLease",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.runtime-e2e",
                "site_id": 1,
                "capability": "device.control",
                "params": {"device_id": "dev-b", "site_id": 2},
                "_session_token": token,
            },
        )
        assert b"error" in response.lower() or b"denied" in response.lower()
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="Linux safe-state E2E requires bwrap")
@pytest.mark.asyncio
async def test_expired_lease_denied_without_regrant(runtime_e2e_package):
    session, settings, session_factory = runtime_e2e_package
    settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
    manager, runtime_id, _ = await start_runtime_with_mode(
        session, settings, session_factory, mode="benign", module_id="integration.runtime-e2e"
    )
    broker = manager.gateway.device_broker
    broker.synthetic.register_device(site_id=1, device_id="dev-1")
    broker.grant_lease(
        runtime_instance_id=runtime_id,
        site_id=1,
        device_id="dev-1",
        capability="device.control",
        ttl_seconds=0.01,
    )
    token = next(
        token
        for token, sess in manager.gateway.session_store._sessions.items()
        if sess.runtime_instance_id == runtime_id and not sess.revoked
    )
    try:
        await asyncio.sleep(0.03)
        response = await manager.gateway._dispatch(
            1,
            "Command",
            {
                "runtime_instance_id": runtime_id,
                "module_id": "integration.runtime-e2e",
                "site_id": 1,
                "capability": "device.control",
                "command": "set_power",
                "params": {"device_id": "dev-1", "site_id": 1, "power_w": 1000},
                "_session_token": token,
            },
        )
        assert b"error" in response.lower() or b"denied" in response.lower() or b"lease" in response.lower()
    finally:
        await manager.stop_runtime(runtime_id)
        cleanup_sandbox_env()
