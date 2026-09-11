"""Runtime identity and attestation binding tests."""

from __future__ import annotations

import pytest

from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.platform.modules.isolation.types import IsolatedRuntimeState


@pytest.mark.asyncio
async def test_handshake_rejects_digest_mismatch(isolation_session):
    session, settings, _ = isolation_session
    repo = IsolatedRuntimeRepository(session)
    record = await repo.create_instance(
        module_id="integration.sandbox-demo",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="expected-digest",
        site_id=1,
        state=IsolatedRuntimeState.HANDSHAKING,
    )
    gateway = ModuleRpcGateway(settings)
    token = gateway.register_runtime(record, permissions=("device.read",), capabilities=("read_status",))
    response = await gateway._handle_handshake(
        1,
        {
            "startup_token": token,
            "runtime_instance_id": record.runtime_instance_id,
            "module_id": record.module_id,
            "version": record.version,
            "artifact_sha256": "wrong-digest",
            "protocol_version": settings.isolated_runtime_protocol_version,
        },
    )
    assert b"digest mismatch" in response.lower()


@pytest.mark.asyncio
async def test_handshake_rejects_version_mismatch(isolation_session):
    session, settings, _ = isolation_session
    repo = IsolatedRuntimeRepository(session)
    record = await repo.create_instance(
        module_id="integration.sandbox-demo",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc123",
        site_id=1,
        state=IsolatedRuntimeState.HANDSHAKING,
    )
    gateway = ModuleRpcGateway(settings)
    token = gateway.register_runtime(record, permissions=("device.read",), capabilities=("read_status",))
    response = await gateway._handle_handshake(
        1,
        {
            "startup_token": token,
            "runtime_instance_id": record.runtime_instance_id,
            "module_id": record.module_id,
            "version": "9.9.9",
            "artifact_sha256": "abc123",
            "protocol_version": settings.isolated_runtime_protocol_version,
        },
    )
    assert b"identity mismatch" in response.lower()
