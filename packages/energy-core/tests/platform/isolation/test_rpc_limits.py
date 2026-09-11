"""RPC payload and rate limit tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.isolation.rpc.protocol import RpcProtocolError, decode_request
from energy_core.platform.modules.isolation.types import RpcErrorCode


def test_decode_rejects_oversized_payload():
    raw = b"x" * 4097
    with pytest.raises(RpcProtocolError) as exc:
        decode_request(raw, max_bytes=4096)
    assert exc.value.code == RpcErrorCode.PAYLOAD_TOO_LARGE


def test_decode_rejects_malformed_json():
    with pytest.raises(RpcProtocolError) as exc:
        decode_request(b"not-json\n", max_bytes=4096)
    assert exc.value.code == RpcErrorCode.INVALID_REQUEST


def test_decode_rejects_missing_method():
    with pytest.raises(RpcProtocolError) as exc:
        decode_request(b'{"jsonrpc":"2.0","id":1,"params":{}}\n', max_bytes=4096)
    assert exc.value.code == RpcErrorCode.INVALID_REQUEST


@pytest.mark.asyncio
async def test_gateway_rejects_unknown_method(isolation_session):
    session, settings, _ = isolation_session
    from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
    from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
    from energy_core.platform.modules.isolation.types import IsolatedRuntimeState

    repo = IsolatedRuntimeRepository(session)
    record = await repo.create_instance(
        module_id="integration.sandbox-demo",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="abc",
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    gateway = ModuleRpcGateway(settings)
    token = gateway.register_runtime(record, permissions=("device.read",), capabilities=("read_status",))
    session_obj = gateway.session_store.create_session(
        runtime_instance_id=record.runtime_instance_id,
        module_id=record.module_id,
        site_id=record.site_id,
    )
    response = await gateway._dispatch(
        1,
        "Execute",
        {
            "runtime_instance_id": record.runtime_instance_id,
            "module_id": record.module_id,
            "site_id": record.site_id,
            "_session_token": session_obj.session_token,
        },
    )
    assert b"unknown method" in response.lower()
