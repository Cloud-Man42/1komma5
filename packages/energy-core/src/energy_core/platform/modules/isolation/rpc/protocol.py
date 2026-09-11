"""JSON-RPC protocol helpers."""

from __future__ import annotations

import json
from typing import Any

from energy_core.platform.modules.isolation.types import RpcErrorCode


class RpcProtocolError(Exception):
    def __init__(self, message: str, *, code: RpcErrorCode) -> None:
        super().__init__(message)
        self.code = code


def encode_response(*, request_id: int | str | None, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> bytes:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result or {}
    return (json.dumps(payload) + "\n").encode("utf-8")


def decode_request(raw: bytes, *, max_bytes: int) -> tuple[int | str | None, str, dict[str, Any]]:
    if len(raw) > max_bytes:
        raise RpcProtocolError("payload too large", code=RpcErrorCode.PAYLOAD_TOO_LARGE)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RpcProtocolError("malformed json", code=RpcErrorCode.INVALID_REQUEST) from exc
    if payload.get("jsonrpc") != "2.0":
        raise RpcProtocolError("invalid jsonrpc version", code=RpcErrorCode.INVALID_REQUEST)
    method = payload.get("method")
    if not isinstance(method, str):
        raise RpcProtocolError("missing method", code=RpcErrorCode.INVALID_REQUEST)
    params = payload.get("params") or {}
    if not isinstance(params, dict):
        raise RpcProtocolError("params must be object", code=RpcErrorCode.INVALID_REQUEST)
    return payload.get("id"), method, params


def rpc_error(code: RpcErrorCode, message: str) -> dict[str, Any]:
    return {"code": code.value, "message": message}
