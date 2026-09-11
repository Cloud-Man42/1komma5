"""RPC auth tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.isolation.rpc.auth import RuntimeSessionStore
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState


def test_startup_token_single_use():
    store = RuntimeSessionStore()
    token = store.issue_startup_token("runtime-1")
    assert store.consume_startup_token(token, expected_instance_id="runtime-1")
    assert not store.consume_startup_token(token, expected_instance_id="runtime-1")


def test_session_rejects_impersonation():
    store = RuntimeSessionStore()
    session = store.create_session(runtime_instance_id="runtime-a", module_id="mod-a", site_id=1)
    assert store.validate_session(
        session.session_token,
        runtime_instance_id="runtime-b",
        module_id="mod-a",
        site_id=1,
    ) is None


def test_revoked_runtime_rejects_session():
    store = RuntimeSessionStore()
    session = store.create_session(runtime_instance_id="runtime-a", module_id="mod-a", site_id=1)
    store.revoke_runtime("runtime-a")
    assert store.validate_session(
        session.session_token,
        runtime_instance_id="runtime-a",
        module_id="mod-a",
        site_id=1,
    ) is None


def test_session_replay_after_revoke():
    store = RuntimeSessionStore()
    session = store.create_session(runtime_instance_id="runtime-a", module_id="mod-a", site_id=1)
    token = session.session_token
    store.revoke_runtime("runtime-a")
    assert store.validate_session(token, runtime_instance_id="runtime-a", module_id="mod-a", site_id=1) is None


@pytest.mark.asyncio
async def test_gateway_rejects_cross_runtime_session(isolation_session):
    session, settings, _ = isolation_session
    repo = IsolatedRuntimeRepository(session)
    record_a = await repo.create_instance(
        module_id="mod-a",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    record_b = await repo.create_instance(
        module_id="mod-b",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="def",
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    gateway = ModuleRpcGateway(settings)
    gateway.register_runtime(record_a, permissions=("device.read",), capabilities=("read_status",))
    gateway.register_runtime(record_b, permissions=("device.read",), capabilities=("read_status",))
    session_a = gateway.session_store.create_session(
        runtime_instance_id=record_a.runtime_instance_id,
        module_id=record_a.module_id,
        site_id=record_a.site_id,
    )
    response = await gateway._dispatch(
        1,
        "GetHealth",
        {
            "runtime_instance_id": record_b.runtime_instance_id,
            "module_id": record_b.module_id,
            "site_id": record_b.site_id,
            "_session_token": session_a.session_token,
        },
    )
    assert b"invalid session" in response.lower()
