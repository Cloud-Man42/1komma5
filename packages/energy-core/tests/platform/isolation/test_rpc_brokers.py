"""RPC broker wiring tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState


@pytest.mark.asyncio
async def test_get_secret_rpc_requires_permission(isolation_session):
    session, settings, _ = isolation_session
    repo = IsolatedRuntimeRepository(session)
    record = await repo.create_instance(
        module_id="mod-a",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    gateway = ModuleRpcGateway(settings)
    gateway.register_runtime(record, permissions=("device.read",), capabilities=("read_status",))
    session_obj = gateway.session_store.create_session(
        runtime_instance_id=record.runtime_instance_id,
        module_id=record.module_id,
        site_id=record.site_id,
    )
    response = await gateway._dispatch(
        1,
        "GetSecret",
        {
            "runtime_instance_id": record.runtime_instance_id,
            "module_id": record.module_id,
            "site_id": record.site_id,
            "secret_ref": "api-key",
            "_session_token": session_obj.session_token,
        },
    )
    assert b"permission" in response.lower() or b"denied" in response.lower()


@pytest.mark.asyncio
async def test_network_request_rpc_requires_permission(isolation_session):
    session, settings, _ = isolation_session
    repo = IsolatedRuntimeRepository(session)
    record = await repo.create_instance(
        module_id="mod-a",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    gateway = ModuleRpcGateway(settings)
    gateway.register_runtime(record, permissions=("device.read",), capabilities=("read_status",))
    session_obj = gateway.session_store.create_session(
        runtime_instance_id=record.runtime_instance_id,
        module_id=record.module_id,
        site_id=record.site_id,
    )
    response = await gateway._dispatch(
        1,
        "NetworkRequest",
        {
            "runtime_instance_id": record.runtime_instance_id,
            "module_id": record.module_id,
            "site_id": record.site_id,
            "url": "https://example.com/",
            "_session_token": session_obj.session_token,
        },
    )
    assert b"network permission" in response.lower() or b"denied" in response.lower()
