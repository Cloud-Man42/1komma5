"""In-process L1 cache with optional Redis L2 and single-flight coalescing."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Protocol

from energy_core.config import Settings, get_settings


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


class TieredCacheService:
    """L1 in-memory cache with optional Redis L2."""

    def __init__(
        self,
        l1: InMemoryCacheService,
        l2: Any | None,
        *,
        l1_warm_ttl_seconds: float = 5.0,
        l2_min_ttl_seconds: float = 60.0,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._l1_warm_ttl_seconds = l1_warm_ttl_seconds
        self._l2_min_ttl_seconds = l2_min_ttl_seconds

    @property
    def redis_configured(self) -> bool:
        return self._l2 is not None and getattr(self._l2, "configured", False)

    @property
    def redis_available(self) -> bool:
        return self._l2 is not None and getattr(self._l2, "available", False)

    async def get(self, key: str) -> Any | None:
        cached = await self._l1.get(key)
        if cached is not None:
            return cached
        if self._l2 is None:
            return None
        cached = await self._l2.get(key)
        if cached is not None:
            await self._l1.set(key, cached, ttl_seconds=self._l1_warm_ttl_seconds)
        return cached

    async def set(self, key: str, value: Any, *, ttl_seconds: float) -> None:
        await self._l1.set(key, value, ttl_seconds=ttl_seconds)
        if self._l2 is not None:
            await self._l2.set(
                key,
                value,
                ttl_seconds=max(ttl_seconds, self._l2_min_ttl_seconds),
            )

    async def invalidate(self, key: str) -> None:
        await self._l1.invalidate(key)
        if self._l2 is not None:
            await self._l2.invalidate(key)

    async def get_or_set(self, key: str, factory, *, ttl_seconds: float) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await self._l1.get_or_set(key, factory, ttl_seconds=ttl_seconds)
        if self._l2 is not None:
            await self._l2.set(
                key,
                value,
                ttl_seconds=max(ttl_seconds, self._l2_min_ttl_seconds),
            )
        return value


_cache_singleton: InMemoryCacheService | TieredCacheService | None = None
_cache_settings_key: str | None = None


def build_cache_service(settings: Settings) -> InMemoryCacheService | TieredCacheService:
    l1 = InMemoryCacheService()
    redis_url = (settings.redis_url or "").strip()
    if not redis_url:
        return l1
    from energy_core.cache.redis import RedisCacheService

    l2 = RedisCacheService(redis_url, default_ttl_seconds=settings.snapshot_redis_cache_ttl_seconds)
    return TieredCacheService(
        l1,
        l2,
        l1_warm_ttl_seconds=60.0,
        l2_min_ttl_seconds=settings.snapshot_redis_cache_ttl_seconds,
    )


def get_cache_service(settings: Settings | None = None) -> InMemoryCacheService | TieredCacheService:
    global _cache_singleton, _cache_settings_key
    settings = settings or get_settings()
    key = f"{settings.redis_url}|{settings.snapshot_redis_cache_ttl_seconds}"
    if _cache_singleton is None or _cache_settings_key != key:
        _cache_singleton = build_cache_service(settings)
        _cache_settings_key = key
    return _cache_singleton


def reset_cache_service() -> None:
    global _cache_singleton, _cache_settings_key
    _cache_singleton = None
    _cache_settings_key = None


def cache_service_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    service = get_cache_service(settings)
    if isinstance(service, TieredCacheService):
        return {
            "backend": "memory+redis",
            "redis_configured": service.redis_configured,
            "redis_available": service.redis_available,
            "snapshot_pubsub_configured": service.redis_configured,
            "snapshot_pubsub_available": False,
        }
    return {
        "backend": "memory",
        "redis_configured": bool((settings.redis_url or "").strip()),
        "redis_available": False,
        "snapshot_pubsub_configured": bool((settings.redis_url or "").strip()),
        "snapshot_pubsub_available": False,
    }


async def cache_service_status_async(settings: Settings | None = None) -> dict[str, Any]:
    from energy_core.cache.snapshot_pubsub import snapshot_pubsub_status

    settings = settings or get_settings()
    service = get_cache_service(settings)
    if isinstance(service, TieredCacheService) and service._l2 is not None:
        await service._l2.get("__emic:cache:probe__")
    status = cache_service_status(settings)
    status.update(await snapshot_pubsub_status(settings))
    return status


def site_snapshot_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:snapshot"


def site_dashboard_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:dashboard"


def financial_stats_cache_key(site_id: int, period: str, year: int | None) -> str:
    year_part = str(year) if year is not None else "all"
    return f"emic:site:{site_id}:financial:{period}:{year_part}"


def solar_forecast_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:solar:forecast"


def current_price_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:prices:current"


def horizon_optimizer_cache_key(site_id: int) -> str:
    return f"emic:site:{site_id}:horizon-optimizer"
