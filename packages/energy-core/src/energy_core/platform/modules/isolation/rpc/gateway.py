"""Host-side RPC gateway for isolated module workers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

from energy_core.config import Settings
from energy_core.platform.modules.brokers.device_control_broker import DeviceControlBroker
from energy_core.platform.modules.brokers.network_broker import NetworkBroker
from energy_core.platform.modules.brokers.secret_broker import SecretBroker
from energy_core.platform.modules.brokers.data_read_broker import DataReadBroker
from energy_core.platform.modules.isolation.rpc.auth import RuntimeSessionStore
from energy_core.platform.modules.isolation.rpc.protocol import decode_request, encode_response, rpc_error
from energy_core.platform.modules.isolation.types import IsolatedRuntimeRecord, RpcErrorCode, RuntimeEventType

logger = logging.getLogger(__name__)

Handler = Callable[[IsolatedRuntimeRecord, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ActiveRuntimeContext:
    record: IsolatedRuntimeRecord
    permissions: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    site_config: dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(UTC))
    bootstrap_ready: bool = False
    module_ready: bool = False


class ModuleRpcGateway:
    def __init__(
        self,
        settings: Settings,
        *,
        secret_broker: SecretBroker | None = None,
        network_broker: NetworkBroker | None = None,
        device_broker: DeviceControlBroker | None = None,
        data_broker: DataReadBroker | None = None,
        audit_callback: Callable[..., Awaitable[None]] | None = None,
        heartbeat_callback: Callable[[str], Awaitable[None]] | None = None,
        climate_publish_callback: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        self._settings = settings
        self._sessions = RuntimeSessionStore()
        self._climate_publish = climate_publish_callback
        self._secret = secret_broker or SecretBroker(settings)
        self._network = network_broker or NetworkBroker(settings)
        self._device = device_broker or DeviceControlBroker(settings)
        self._data = data_broker or DataReadBroker(settings)
        self._audit = audit_callback
        self._heartbeat = heartbeat_callback
        self._active: dict[str, ActiveRuntimeContext] = {}
        self._server: asyncio.AbstractServer | None = None
        self._listen_address: str | None = None
        self._rate_window: dict[str, list[float]] = defaultdict(list)
        self._inflight: dict[str, int] = defaultdict(int)

    @property
    def session_store(self) -> RuntimeSessionStore:
        return self._sessions

    @property
    def device_broker(self) -> DeviceControlBroker:
        return self._device

    @property
    def secret_broker(self) -> SecretBroker:
        return self._secret

    @property
    def network_broker(self) -> NetworkBroker:
        return self._network

    def listen_address(self) -> str | None:
        return self._listen_address

    def is_bootstrap_ready(self, runtime_instance_id: str) -> bool:
        ctx = self._active.get(runtime_instance_id)
        return ctx is not None and ctx.bootstrap_ready

    def is_module_ready(self, runtime_instance_id: str) -> bool:
        ctx = self._active.get(runtime_instance_id)
        return ctx is not None and ctx.module_ready

    def is_process_ready(self, runtime_instance_id: str) -> bool:
        ctx = self._active.get(runtime_instance_id)
        return ctx is not None and ctx.bootstrap_ready and ctx.module_ready

    def register_runtime(
        self,
        record: IsolatedRuntimeRecord,
        *,
        permissions: tuple[str, ...],
        capabilities: tuple[str, ...],
        site_config: dict[str, Any] | None = None,
    ) -> str:
        self._active[record.runtime_instance_id] = ActiveRuntimeContext(
            record=record,
            permissions=permissions,
            capabilities=capabilities,
            site_config=dict(site_config or {}),
        )
        return self._sessions.issue_startup_token(record.runtime_instance_id)

    def unregister_runtime(self, runtime_instance_id: str) -> None:
        self._active.pop(runtime_instance_id, None)
        self._sessions.revoke_runtime(runtime_instance_id)

    async def start_server(self, socket_path: str) -> None:
        if sys.platform == "win32":
            self._server = await asyncio.start_server(self._handle_client, host="127.0.0.1", port=0)
            sockets = self._server.sockets or []
            if not sockets:
                raise RuntimeError("failed to bind RPC server")
            host, port = sockets[0].getsockname()[:2]
            self._listen_address = f"tcp:{host}:{port}"
            return
        path = Path(socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.geteuid() == 0:
            module_uid = self._settings.isolated_runtime_module_uid
            module_gid = self._settings.isolated_runtime_module_gid
            for parent in path.parents:
                if not parent.exists():
                    continue
                try:
                    os.chmod(parent, (os.stat(parent).st_mode | 0o0111) & 0o777)
                except OSError:
                    pass
                if parent.parent == parent:
                    break
            try:
                os.chown(path.parent, module_uid, module_gid)
                os.chmod(path.parent, 0o700)
            except OSError:
                pass
        if path.exists():
            path.unlink()
        self._server = await asyncio.start_unix_server(self._handle_client, path=str(path))
        os.chmod(path, 0o600)
        if os.geteuid() == 0:
            try:
                os.chown(path, self._settings.isolated_runtime_module_uid, self._settings.isolated_runtime_module_gid)
            except OSError:
                pass
        self._listen_address = str(path)

    async def stop_server(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw = await asyncio.wait_for(reader.readline(), timeout=self._settings.isolated_runtime_handshake_timeout_seconds)
            if not raw:
                return
            request_id, method, params = decode_request(raw, max_bytes=self._settings.isolated_runtime_rpc_max_bytes)
            response = await self._dispatch(request_id, method, params)
            writer.write(response)
            await writer.drain()
        except Exception as exc:
            logger.warning("rpc client error: %s", exc)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch(self, request_id: int | str | None, method: str, params: dict[str, Any]) -> bytes:
        runtime_instance_id = str(params.get("runtime_instance_id", ""))
        module_id = str(params.get("module_id", ""))
        site_id = int(params.get("site_id", 0) or 0)
        if method == "Handshake":
            return await self._handle_handshake(request_id, params)
        if method == "ReportPrivilegeDropFailed":
            return await self._handle_privilege_drop_failed(request_id, params)
        session_token = params.pop("_session_token", None) or params.get("session_token")
        if not isinstance(session_token, str):
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "missing session"))
        session = self._sessions.validate_session(
            session_token,
            runtime_instance_id=runtime_instance_id,
            module_id=module_id,
            site_id=site_id,
        )
        if session is None:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "invalid session"))
        ctx = self._active.get(runtime_instance_id)
        if ctx is None:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.NOT_RUNNING, "runtime not active"))
        if not self._rate_ok(runtime_instance_id):
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.RATE_LIMITED, "rate limit"))
        if self._inflight[runtime_instance_id] >= self._settings.isolated_runtime_rpc_max_concurrent:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.RATE_LIMITED, "too many concurrent"))
        self._inflight[runtime_instance_id] += 1
        try:
            handlers: dict[str, Handler] = {
                "BootstrapReady": self._handle_bootstrap_ready,
                "ReportModuleReady": self._handle_module_ready,
                "GetHealth": self._handle_health,
                "GetCapabilities": self._handle_capabilities,
                "Read": self._handle_read,
                "Command": self._handle_command,
                "AcquireControlLease": self._handle_acquire_lease,
                "RenewControlLease": self._handle_renew_lease,
                "GetConfig": self._handle_config,
                "GetSecret": self._handle_secret,
                "NetworkRequest": self._handle_network,
                "PublishReadings": self._handle_publish_readings,
                "ReportMetric": self._handle_metric,
                "Stop": self._handle_stop,
            }
            handler = handlers.get(method)
            if handler is None:
                return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.INVALID_REQUEST, "unknown method"))
            result = await handler(ctx.record, params)
            if method == "GetHealth":
                ctx.last_heartbeat = datetime.now(UTC)
                if self._heartbeat is not None:
                    await self._heartbeat(ctx.record.runtime_instance_id)
            return encode_response(request_id=request_id, result=result)
        except PermissionError as exc:
            await self._audit_event(ctx.record, RuntimeEventType.PERMISSION_DENIED, {"method": method, "detail": str(exc)})
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.CAPABILITY_DENIED, str(exc)))
        except ValueError as exc:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.BROKER_REJECTED, str(exc)))
        finally:
            self._inflight[runtime_instance_id] -= 1

    async def _handle_handshake(self, request_id: int | str | None, params: dict[str, Any]) -> bytes:
        startup_token = params.get("startup_token")
        runtime_instance_id = str(params.get("runtime_instance_id", ""))
        module_id = str(params.get("module_id", ""))
        version = str(params.get("version", ""))
        artifact_sha256 = str(params.get("artifact_sha256", ""))
        protocol_version = int(params.get("protocol_version", 0) or 0)
        ctx = self._active.get(runtime_instance_id)
        if ctx is None:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.NOT_RUNNING, "unknown runtime"))
        if protocol_version != self._settings.isolated_runtime_protocol_version:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.PROTOCOL_MISMATCH, "protocol mismatch"))
        if ctx.record.module_id != module_id or ctx.record.version != version:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "identity mismatch"))
        if ctx.record.artifact_sha256.lower() != artifact_sha256.lower():
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "digest mismatch"))
        if not isinstance(startup_token, str) or not self._sessions.consume_startup_token(startup_token, expected_instance_id=runtime_instance_id):
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "startup token invalid"))
        session = self._sessions.create_session(
            runtime_instance_id=runtime_instance_id,
            module_id=module_id,
            site_id=ctx.record.site_id,
        )
        await self._audit_event(ctx.record, RuntimeEventType.HANDSHAKE, {"module_id": module_id})
        return encode_response(
            request_id=request_id,
            result={
                "session_token": session.session_token,
                "protocol_version": self._settings.isolated_runtime_protocol_version,
            },
        )

    async def _handle_privilege_drop_failed(self, request_id: int | str | None, params: dict[str, Any]) -> bytes:
        runtime_instance_id = str(params.get("runtime_instance_id", ""))
        module_id = str(params.get("module_id", ""))
        site_id = int(params.get("site_id", 0) or 0)
        stage = str(params.get("stage", "unknown"))
        reason = str(params.get("reason", "privilege drop failed"))
        session_token = params.get("_session_token") or params.get("session_token")
        ctx = self._active.get(runtime_instance_id)
        if ctx is None:
            return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.NOT_RUNNING, "unknown runtime"))
        if isinstance(session_token, str):
            session = self._sessions.validate_session(
                session_token,
                runtime_instance_id=runtime_instance_id,
                module_id=module_id,
                site_id=site_id,
            )
            if session is None:
                return encode_response(request_id=request_id, error=rpc_error(RpcErrorCode.AUTH_FAILED, "invalid session"))
        self._sessions.revoke_runtime(runtime_instance_id)
        ctx.bootstrap_ready = False
        await self._audit_event(
            ctx.record,
            RuntimeEventType.PRIVILEGE_DROP_FAILED,
            {"stage": stage, "reason": reason},
        )
        return encode_response(request_id=request_id, result={"ok": True, "terminated": True})

    async def _handle_bootstrap_ready(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        ctx = self._active.get(record.runtime_instance_id)
        if ctx is None:
            raise ValueError("runtime not active")
        uid = int(params.get("uid", -1))
        gid = int(params.get("gid", -1))
        expected_uid = self._settings.isolated_runtime_module_uid
        expected_gid = self._settings.isolated_runtime_module_gid
        if uid >= 0 and gid >= 0:
            if uid != expected_uid or gid != expected_gid:
                raise PermissionError(f"identity mismatch after drop: uid={uid} gid={gid}")
        ctx.bootstrap_ready = True
        return {"ok": True, "uid": uid, "gid": gid}

    async def _handle_module_ready(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        ctx = self._active.get(record.runtime_instance_id)
        if ctx is None:
            raise ValueError("runtime not active")
        ctx.module_ready = True
        return {"ok": True}

    async def _handle_health(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        return {"healthy": True, "state": record.state.value, "runtime_instance_id": record.runtime_instance_id}

    async def _handle_capabilities(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        ctx = self._active[record.runtime_instance_id]
        return {"capabilities": list(ctx.capabilities)}

    async def _handle_read(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        capability = str(params.get("capability", ""))
        read_params = params.get("params") or {}
        if not isinstance(read_params, dict):
            raise ValueError("params must be object")
        ctx = self._active[record.runtime_instance_id]
        return await self._data.read(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            capability=capability,
            params=read_params,
            permissions=ctx.permissions,
            capabilities=ctx.capabilities,
        )

    async def _handle_command(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        capability = str(params.get("capability", ""))
        command = str(params.get("command", ""))
        cmd_params = params.get("params") or {}
        if not isinstance(cmd_params, dict):
            raise ValueError("params must be object")
        return await self._device.command(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            capability=capability,
            command=command,
            params=cmd_params,
            permissions=self._active[record.runtime_instance_id].permissions,
        )

    async def _handle_acquire_lease(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        capability = str(params.get("capability", "device.control"))
        lease_params = params.get("params") or {}
        if not isinstance(lease_params, dict):
            raise ValueError("params must be object")
        return await self._device.acquire_lease(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            capability=capability,
            params=lease_params,
            permissions=self._active[record.runtime_instance_id].permissions,
        )

    async def _handle_renew_lease(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        capability = str(params.get("capability", "device.control"))
        lease_params = params.get("params") or {}
        if not isinstance(lease_params, dict):
            raise ValueError("params must be object")
        return await self._device.renew_lease(
            runtime_instance_id=record.runtime_instance_id,
            site_id=record.site_id,
            capability=capability,
            params=lease_params,
            permissions=self._active[record.runtime_instance_id].permissions,
        )

    async def _handle_config(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        ctx = self._active.get(record.runtime_instance_id)
        key = params.get("key")
        config = {"module_id": record.module_id, "site_id": record.site_id}
        if ctx is not None:
            config.update(ctx.site_config)
        if isinstance(key, str) and key:
            return {"config": {key: config.get(key)}}
        return {"config": config}

    async def _handle_publish_readings(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        readings = params.get("readings")
        if not isinstance(readings, list):
            raise ValueError("readings must be a list")
        requested_site = params.get("site_id")
        if requested_site is not None and int(requested_site) != record.site_id:
            raise PermissionError("cross-site publish denied")
        ctx = self._active.get(record.runtime_instance_id)
        caps = ctx.capabilities if ctx else ()
        allowed = any(str(c).startswith("hvac.read") for c in caps) or "device.read" in (ctx.permissions if ctx else ())
        if not allowed:
            raise PermissionError("publish not permitted for module capabilities")
        if self._climate_publish is None:
            raise ValueError("climate publish not configured")
        await self._climate_publish(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            readings=readings,
        )
        return {"ok": True, "count": len(readings)}

    async def _handle_secret(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        secret_ref = str(params.get("secret_ref", ""))
        if not secret_ref:
            raise ValueError("secret_ref required")
        value = await self._secret.get_secret(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            secret_ref=secret_ref,
            permissions=self._active[record.runtime_instance_id].permissions,
        )
        return {"secret_ref": secret_ref, "value": value}

    async def _handle_network(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        url = str(params.get("url", ""))
        method = str(params.get("method", "GET"))
        headers = params.get("headers") or {}
        if not isinstance(headers, dict):
            raise ValueError("headers must be object")
        return await self._network.request(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            url=url,
            method=method,
            permissions=self._active[record.runtime_instance_id].permissions,
            headers={str(k): str(v) for k, v in headers.items()},
        )

    async def _handle_metric(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True}

    async def _handle_stop(self, record: IsolatedRuntimeRecord, params: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "stopping": True}

    def _rate_ok(self, runtime_instance_id: str) -> bool:
        now = time.time()
        window = self._rate_window[runtime_instance_id]
        window[:] = [t for t in window if now - t < 60.0]
        if len(window) >= self._settings.isolated_runtime_rpc_rate_limit_per_minute:
            return False
        window.append(now)
        return True

    async def _audit_event(self, record: IsolatedRuntimeRecord, event_type: RuntimeEventType, detail: dict[str, Any]) -> None:
        if self._audit is None:
            return
        await self._audit(
            runtime_instance_id=record.runtime_instance_id,
            event_type=event_type,
            module_id=record.module_id,
            site_id=record.site_id,
            detail=detail,
        )
