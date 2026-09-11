"""Distributed module runtime state via Redis (collector authority, backend read)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from energy_core.config import Settings, get_settings
from energy_core.platform.modules.types import ModuleHealthStatus, RuntimeStatus

logger = logging.getLogger(__name__)

RUNTIME_KEY_PREFIX = "emic:runtime:"
RUNTIME_TTL_SECONDS = 90
COLLECTOR_INSTANCE_ID = str(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class RuntimeStateSnapshot:
    site_id: int
    module_id: str
    runtime_state: RuntimeStatus
    health_state: ModuleHealthStatus = ModuleHealthStatus.UNKNOWN
    started_at: str | None = None
    last_transition_at: str | None = None
    last_heartbeat_at: str | None = None
    last_error: str | None = None
    instance_id: str | None = None
    module_version: str | None = None
    package_checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id,
            "module_id": self.module_id,
            "runtime_state": self.runtime_state.value,
            "health_state": self.health_state.value,
            "started_at": self.started_at,
            "last_transition_at": self.last_transition_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_error": self.last_error,
            "instance_id": self.instance_id,
            "module_version": self.module_version,
            "package_checksum": self.package_checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeStateSnapshot | None:
        try:
            site_id = int(data["site_id"])
            module_id = str(data["module_id"])
            runtime_state = RuntimeStatus(str(data["runtime_state"]))
            health_raw = data.get("health_state")
            health_state = (
                ModuleHealthStatus(str(health_raw))
                if health_raw
                else ModuleHealthStatus.UNKNOWN
            )
        except (KeyError, TypeError, ValueError):
            return None
        return cls(
            site_id=site_id,
            module_id=module_id,
            runtime_state=runtime_state,
            health_state=health_state,
            started_at=data.get("started_at"),
            last_transition_at=data.get("last_transition_at"),
            last_heartbeat_at=data.get("last_heartbeat_at"),
            last_error=data.get("last_error"),
            instance_id=data.get("instance_id"),
            module_version=data.get("module_version"),
            package_checksum=data.get("package_checksum"),
        )


def _runtime_key(site_id: int, module_id: str) -> str:
    return f"{RUNTIME_KEY_PREFIX}{site_id}:{module_id}"


def _site_pattern(site_id: int) -> str:
    return f"{RUNTIME_KEY_PREFIX}{site_id}:*"


class ModuleRuntimeStateStore:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url.strip()
        self._client: Any | None = None
        self._available = bool(self._redis_url)

    async def _get_client(self) -> Any | None:
        if not self._available or not self._redis_url:
            return None
        if self._client is not None:
            return self._client
        try:
            from redis.asyncio import Redis

            client = Redis.from_url(self._redis_url, decode_responses=True)
            await client.ping()
            self._client = client
            return self._client
        except Exception:
            logger.warning("Module runtime state store unavailable", exc_info=True)
            self._available = False
            self._client = None
            return None

    async def publish(self, snapshot: RuntimeStateSnapshot) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        now_iso = datetime.now(UTC).isoformat()
        payload = snapshot.to_dict()
        if payload.get("last_transition_at") is None:
            payload["last_transition_at"] = now_iso
        if snapshot.runtime_state == RuntimeStatus.RUNNING:
            payload["last_heartbeat_at"] = now_iso
        try:
            key = _runtime_key(snapshot.site_id, snapshot.module_id)
            await client.set(key, json.dumps(payload), ex=RUNTIME_TTL_SECONDS)
            return True
        except Exception:
            logger.debug(
                "Runtime state publish failed site=%s module=%s",
                snapshot.site_id,
                snapshot.module_id,
                exc_info=True,
            )
            return False

    async def refresh_heartbeat(self, site_id: int, module_id: str) -> bool:
        client = await self._get_client()
        if client is None:
            return False
        key = _runtime_key(site_id, module_id)
        try:
            raw = await client.get(key)
            if not raw:
                return False
            data = json.loads(raw)
            if data.get("runtime_state") != RuntimeStatus.RUNNING.value:
                return False
            data["last_heartbeat_at"] = datetime.now(UTC).isoformat()
            await client.set(key, json.dumps(data), ex=RUNTIME_TTL_SECONDS)
            return True
        except Exception:
            logger.debug(
                "Runtime heartbeat refresh failed site=%s module=%s",
                site_id,
                module_id,
                exc_info=True,
            )
            return False

    async def read_site(self, site_id: int) -> dict[str, RuntimeStateSnapshot]:
        client = await self._get_client()
        if client is None:
            return {}
        result: dict[str, RuntimeStateSnapshot] = {}
        try:
            keys = [key async for key in client.scan_iter(match=_site_pattern(site_id), count=100)]
            if not keys:
                return {}
            values = await client.mget(keys)
            for raw in values:
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                snapshot = RuntimeStateSnapshot.from_dict(data)
                if snapshot is not None:
                    result[snapshot.module_id] = snapshot
        except Exception:
            logger.debug("Runtime state read failed site=%s", site_id, exc_info=True)
        return result

    async def delete(self, site_id: int, module_id: str) -> None:
        client = await self._get_client()
        if client is None:
            return
        try:
            await client.delete(_runtime_key(site_id, module_id))
        except Exception:
            logger.debug(
                "Runtime state delete failed site=%s module=%s",
                site_id,
                module_id,
                exc_info=True,
            )


_store_singleton: ModuleRuntimeStateStore | None = None
_store_key: str | None = None


def get_runtime_state_store(settings: Settings | None = None) -> ModuleRuntimeStateStore:
    global _store_singleton, _store_key
    settings = settings or get_settings()
    key = settings.redis_url or ""
    if _store_singleton is None or _store_key != key:
        _store_singleton = ModuleRuntimeStateStore(key)
        _store_key = key
    return _store_singleton


async def publish_runtime_state(
    settings: Settings,
    *,
    site_id: int,
    module_id: str,
    runtime_state: RuntimeStatus,
    last_error: str | None = None,
    health_state: ModuleHealthStatus = ModuleHealthStatus.UNKNOWN,
    started_at: str | None = None,
    module_version: str | None = None,
    package_checksum: str | None = None,
) -> bool:
    if not (settings.redis_url or "").strip():
        return False
    now_iso = datetime.now(UTC).isoformat()
    snapshot = RuntimeStateSnapshot(
        site_id=site_id,
        module_id=module_id,
        runtime_state=runtime_state,
        health_state=health_state,
        started_at=started_at or (now_iso if runtime_state == RuntimeStatus.RUNNING else None),
        last_transition_at=now_iso,
        last_heartbeat_at=now_iso if runtime_state == RuntimeStatus.RUNNING else None,
        last_error=last_error,
        instance_id=COLLECTOR_INSTANCE_ID,
        module_version=module_version,
        package_checksum=package_checksum,
    )
    return await get_runtime_state_store(settings).publish(snapshot)


async def read_runtime_states(
    settings: Settings,
    site_id: int,
) -> dict[str, RuntimeStateSnapshot]:
    if not (settings.redis_url or "").strip():
        return {}
    return await get_runtime_state_store(settings).read_site(site_id)


async def refresh_runtime_heartbeats(
    settings: Settings,
    site_id: int,
    module_ids: tuple[str, ...],
) -> None:
    if not module_ids or not (settings.redis_url or "").strip():
        return
    store = get_runtime_state_store(settings)
    for module_id in module_ids:
        await store.refresh_heartbeat(site_id, module_id)


def resolve_distributed_runtime_status(
    snapshot: RuntimeStateSnapshot | None,
    *,
    local_state: RuntimeStatus,
    enabled: bool,
    distributed_runtime_expected: bool = False,
) -> RuntimeStatus:
    if not enabled:
        return RuntimeStatus.STOPPED
    if snapshot is not None:
        return snapshot.runtime_state
    if distributed_runtime_expected:
        return RuntimeStatus.UNKNOWN
    return local_state
