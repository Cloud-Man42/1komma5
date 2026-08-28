"""In-process L1 cache with TTL jitter and single-flight coalescing."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Protocol


class ICacheService(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, *, ttl_seconds: float) -> None: ...

    async def invalidate(self, key: str) -> None: ...

    async def get_or_set(self, key: str, factory, *, ttl_seconds: float) -> Any: ...


@dataclass(slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class InMemoryCacheService:
    """Process-local cache with TTL jitter and request coalescing on miss."""

    def __init__(self, jitter_fraction: float = 0.1) -> None:
        self._entries: dict[str, _CacheEntry] = {}
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()
        self._jitter_fraction = jitter_fraction

    def _effective_ttl(self, ttl_seconds: float) -> float:
        if ttl_seconds <= 0:
            return 0.0
        jitter = ttl_seconds * self._jitter_fraction
        return ttl_seconds + random.uniform(-jitter, jitter)

    async def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            self._entries.pop(key, None)
            return
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self._effective_ttl(ttl_seconds),
        )

    async def invalidate(self, key: str) -> None:
        self._entries.pop(key, None)

    async def get_or_set(self, key: str, factory, *, ttl_seconds: float) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached

        async with self._lock:
            cached = await self.get(key)
            if cached is not None:
                return cached
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(factory())
                self._inflight[key] = task

        try:
            value = await task
        finally:
            async with self._lock:
                if self._inflight.get(key) is task:
                    self._inflight.pop(key, None)

        await self.set(key, value, ttl_seconds=ttl_seconds)
        return value


_default_cache = InMemoryCacheService()


def get_cache_service() -> InMemoryCacheService:
    return _default_cache


def site_snapshot_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:snapshot"
