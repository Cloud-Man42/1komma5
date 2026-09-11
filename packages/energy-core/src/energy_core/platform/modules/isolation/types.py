"""Isolated runtime types (Step 5C.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class IsolatedRuntimeState(StrEnum):
    PREPARING = "PREPARING"
    STARTING = "STARTING"
    HANDSHAKING = "HANDSHAKING"
    READY = "READY"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"
    QUARANTINED = "QUARANTINED"
    BLOCKED = "BLOCKED"


class RuntimeEventType(StrEnum):
    PREPARE = "runtime.prepare"
    START = "runtime.start"
    HANDSHAKE = "runtime.handshake"
    READY = "runtime.ready"
    STOP = "runtime.stop"
    CRASH = "runtime.crash"
    QUARANTINE = "runtime.quarantine"
    DENY = "runtime.deny"
    RPC_DENIED = "rpc.denied"
    PERMISSION_DENIED = "permission.denied"
    SECRET_ACCESS = "secret.access"
    NETWORK_REQUEST = "network.request"
    DEVICE_COMMAND = "device.command"
    RESOURCE_LIMIT = "runtime.resource_limit"
    IDENTITY_MISMATCH = "runtime.identity_mismatch"
    REVOCATION_STOP = "runtime.revocation_stop"
    PRIVILEGE_DROP_FAILED = "runtime.privilege_drop_failed"


class RpcErrorCode(StrEnum):
    NOT_RUNNING = "NOT_RUNNING"
    CAPABILITY_DENIED = "CAPABILITY_DENIED"
    BROKER_REJECTED = "BROKER_REJECTED"
    CONFIG_VALIDATION_FAILED = "CONFIG_VALIDATION_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    runtime_instance_id: str
    module_id: str
    version: str
    publisher_id: str
    artifact_sha256: str
    site_id: int
    process_identity: str
    protocol_version: int
    started_at: datetime


@dataclass(frozen=True, slots=True)
class RuntimeAttestation:
    module_id: str
    version: str
    artifact_sha256: str
    runtime_instance_id: str
    protocol_version: int


@dataclass(slots=True)
class IsolatedRuntimeRecord:
    id: int | None
    runtime_instance_id: str
    module_id: str
    version: str
    publisher_id: str
    artifact_sha256: str
    site_id: int
    state: IsolatedRuntimeState
    process_identity: str | None = None
    process_pid: int | None = None
    sandbox_mode: str | None = None
    socket_path: str | None = None
    package_path: str | None = None
    data_path: str | None = None
    protocol_version: int = 1
    restart_count: int = 0
    last_error: str | None = None
    reason_codes: tuple[str, ...] = ()
    permissions_json: str | None = None
    started_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class RuntimeStartRequest:
    module_id: str
    site_id: int
    version: str | None = None
    artifact_sha256: str | None = None
    publisher_id: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeStartResult:
    ok: bool
    runtime_instance_id: str | None = None
    state: IsolatedRuntimeState = IsolatedRuntimeState.BLOCKED
    message: str = ""
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True)
class ControlLeaseRecord:
    id: int | None
    runtime_instance_id: str
    module_id: str
    site_id: int
    device_id: str
    capability: str
    expires_at: datetime
    active: bool = True


@dataclass(frozen=True, slots=True)
class RpcRequestContext:
    runtime_instance_id: str
    module_id: str
    site_id: int
    session_token: str
    method: str
    params: dict = field(default_factory=dict)
