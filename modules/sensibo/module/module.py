"""Sensibo climate module runtime (read-only)."""

from __future__ import annotations

import json
import time
from typing import Any

from adapter import normalize_pod_reading
from sensibo_client import SensiboClient, SensiboClientError


class _HealthGateStatus:
    level = "ok"
    message = "sensibo module ready"


class _StubRpc:
    def get_config(self) -> dict[str, Any]:
        return {"config": {}}

    def get_secret(self, secret_ref: str) -> str:
        return ""

    def network_request(self, **kwargs: Any) -> dict[str, Any]:
        return {"status_code": 200, "body": "{}"}

    def publish_readings(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        return {"accepted": len(readings)}


class SensiboModuleRuntime:
    def __init__(self, ctx: dict[str, Any]) -> None:
        self._ctx = ctx
        self._health_gate_only = bool(ctx.get("_health_gate_only"))
        self._rpc = ctx.get("rpc") if self._health_gate_only else ctx["rpc"]
        self._module_id = str(ctx.get("module_id") or "integration.sensibo")
        self._site_id = int(ctx.get("site_id") or 1)
        self._health = "HEALTHY"
        self._health_message = "ok"
        self._last_success: float | None = None
        self._request_log: list[dict[str, str]] = []

    def start(self) -> None:
        self._health = "HEALTHY"
        self._health_message = "started"

    def tick(self) -> None:
        config = self._rpc.get_config()
        cfg = config.get("config") if isinstance(config, dict) else {}
        if not isinstance(cfg, dict):
            cfg = {}
        credential_ref = str(cfg.get("credential_ref") or "api_key")
        selected = cfg.get("selected_device_ids") or []
        if not isinstance(selected, list):
            selected = []
        try:
            api_key = self._rpc.get_secret(credential_ref)
        except Exception as exc:
            self._health = "UNHEALTHY"
            self._health_message = f"credential error: {exc.__class__.__name__}"
            return

        def request_fn(**kwargs: Any) -> dict[str, Any]:
            method = str(kwargs.get("method") or "GET").upper()
            if method not in {"GET", "HEAD"}:
                raise SensiboClientError(f"write method blocked: {method}")
            self._request_log.append({"method": method, "url": str(kwargs.get("url") or "")})
            return self._rpc.network_request(
                url=str(kwargs["url"]),
                method=method,
                headers=kwargs.get("headers") or {},
                timeout=float(kwargs.get("timeout") or 10.0),
            )

        fixture_pods = self._ctx.get("fixture_pods")
        if fixture_pods is None:
            import os

            raw = os.environ.get("EMIC_SENSIBO_FIXTURE_PODS")
            if raw:
                try:
                    parsed = json.loads(raw)
                    fixture_pods = parsed if isinstance(parsed, list) else None
                except json.JSONDecodeError:
                    fixture_pods = None
        if isinstance(fixture_pods, list):
            pods = [p for p in fixture_pods if isinstance(p, dict)]
        else:
            client = SensiboClient(api_key=api_key, request_fn=request_fn, audit_hook=lambda a: None)
            try:
                pods = client.list_pods()
            except SensiboClientError as exc:
                self._health = "UNHEALTHY" if exc.status in {401, 403} else "DEGRADED"
                self._health_message = str(exc)
                return

        if selected:
            pods = [p for p in pods if str(p.get("id") or p.get("deviceUid") or "") in {str(s) for s in selected}]

        readings: list[dict[str, Any]] = []
        for pod in pods:
            pod_id = str(pod.get("id") or pod.get("deviceUid") or "")
            if not pod_id:
                continue
            if isinstance(fixture_pods, list):
                measurement = pod.get("measurements") if isinstance(pod.get("measurements"), dict) else None
                merged = pod
            else:
                measurements = client.get_measurements(pod_id, limit=1)
                measurement = measurements[0] if measurements else None
                detail = client.get_pod(pod_id)
                merged = {**pod, **detail}
            readings.append(normalize_pod_reading(pod=merged, measurement=measurement, site_id=self._site_id))

        if readings:
            self._rpc.publish_readings(readings)
            self._last_success = time.time()
            self._health = "HEALTHY"
            self._health_message = f"{len(readings)} device(s)"
        else:
            self._health = "DEGRADED"
            self._health_message = "no devices"

    def get_health(self) -> dict[str, Any]:
        return {
            "level": self._health,
            "message": self._health_message,
            "last_success": self._last_success,
        }

    def health(self) -> _HealthGateStatus:
        if self._health_gate_only:
            return _HealthGateStatus()
        level = str(self._health).lower()
        status = _HealthGateStatus()
        if level in {"healthy", "ok"}:
            status.level = "ok"
        elif level in {"degraded"}:
            status.level = "degraded"
        else:
            status.level = "unhealthy"
        status.message = self._health_message
        return status


def build_module(ctx: dict[str, Any] | Any) -> SensiboModuleRuntime:
    if isinstance(ctx, dict):
        rpc = _RpcBridge(ctx)
        return SensiboModuleRuntime({**ctx, "rpc": rpc})
    return SensiboModuleRuntime(
        {
            "module_id": str(getattr(ctx, "module_id", "integration.sensibo")),
            "site_id": int(getattr(ctx, "site_id", None) or 1),
            "rpc": _StubRpc(),
            "_health_gate_only": True,
        }
    )


class _RpcBridge:
    def __init__(self, ctx: dict[str, Any]) -> None:
        self._socket = ctx["rpc_socket"]
        self._token = ctx["session_token"]
        self._client = None

    def _client_instance(self):
        if self._client is None:
            import sys
            from pathlib import Path

            sdk = Path("/sdk")
            if sdk.exists() and str(sdk) not in sys.path:
                sys.path.insert(0, str(sdk))
            from emic_runtime_sdk.client import RuntimeRpcClient

            self._client = RuntimeRpcClient(self._socket, startup_token=self._token)
            self._client._session_token = self._token
        return self._client

    def get_config(self) -> dict[str, Any]:
        return self._client_instance().get_config()

    def get_secret(self, secret_ref: str) -> str:
        return self._client_instance().get_secret(secret_ref)

    def network_request(self, **kwargs: Any) -> dict[str, Any]:
        return self._client_instance().network_request(**kwargs)

    def publish_readings(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        return self._client_instance().publish_readings(readings)
