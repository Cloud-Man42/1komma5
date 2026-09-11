"""Minimal RPC client for isolated module workers."""

from __future__ import annotations

import json
import os
import socket
import sys
from typing import Any


PROTOCOL_VERSION = int(os.environ.get("EMIC_PROTOCOL_VERSION", "1"))


class RpcClientError(Exception):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class RuntimeRpcClient:
    def __init__(self, socket_path: str, *, startup_token: str) -> None:
        self._socket_path = socket_path
        self._startup_token = startup_token
        self._session_token: str | None = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params,
        }
        if self._session_token:
            payload["params"] = {**params, "_session_token": self._session_token}
        data = (json.dumps(payload) + "\n").encode("utf-8")
        if self._socket_path.startswith("tcp:"):
            _, host, port = self._socket_path.split(":", 2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, int(port)))
        elif sys.platform == "win32":
            raise RpcClientError("Unix socket RPC not supported on this platform in worker")
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self._socket_path)
        try:
            sock.sendall(data)
            chunks: list[bytes] = []
            while True:
                part = sock.recv(65536)
                if not part:
                    break
                chunks.append(part)
                if b"\n" in part:
                    break
            raw = b"".join(chunks).split(b"\n", 1)[0]
            response = json.loads(raw.decode("utf-8"))
        finally:
            sock.close()
        if "error" in response:
            err = response["error"]
            raise RpcClientError(str(err.get("message", "rpc error")), code=str(err.get("code", "")))
        result = response.get("result")
        if not isinstance(result, dict):
            raise RpcClientError("invalid rpc result")
        return result

    def handshake(
        self,
        *,
        module_id: str,
        version: str,
        artifact_sha256: str,
        runtime_instance_id: str,
        site_id: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "startup_token": self._startup_token,
            "module_id": module_id,
            "version": version,
            "artifact_sha256": artifact_sha256,
            "runtime_instance_id": runtime_instance_id,
            "protocol_version": PROTOCOL_VERSION,
        }
        if site_id is not None:
            params["site_id"] = site_id
        result = self._send("Handshake", params)
        token = result.get("session_token")
        if not isinstance(token, str) or not token:
            raise RpcClientError("handshake missing session token", code="AUTH_FAILED")
        self._session_token = token
        return result

    def get_health(self) -> dict[str, Any]:
        return self._send("GetHealth", {})

    def get_capabilities(self) -> dict[str, Any]:
        return self._send("GetCapabilities", {})

    def read(self, capability: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._send("Read", {"capability": capability, "params": params or {}})

    def command(self, capability: str, command: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._send("Command", {"capability": capability, "command": command, "params": params or {}})

    def get_config(self, key: str | None = None) -> dict[str, Any]:
        return self._send("GetConfig", {"key": key})

    def get_secret(self, secret_ref: str) -> str:
        result = self._send("GetSecret", {"secret_ref": secret_ref})
        value = result.get("value")
        if not isinstance(value, str):
            raise RpcClientError("secret response invalid")
        return value

    def network_request(
        self,
        *,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"url": url, "method": method, "headers": headers or {}}
        if body is not None:
            params["body"] = body
        if timeout is not None:
            params["timeout"] = timeout
        return self._send("NetworkRequest", params)

    def publish_readings(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        return self._send("PublishReadings", {"readings": readings})

    def report_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> dict[str, Any]:
        return self._send("ReportMetric", {"name": name, "value": value, "tags": tags or {}})

    def stop(self) -> dict[str, Any]:
        return self._send("Stop", {})
