"""Tiered and Redis cache tests."""

from __future__ import annotations

import pytest

from energy_core.cache.redis import RedisCacheService
from energy_core.cache.service import (
    InMemoryCacheService,
    TieredCacheService,
    build_cache_service,
    reset_cache_service,
)
from energy_core.config import Settings


class _FakeRedisL2:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}
        self.configured = True
        self.available = True

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value, *, ttl_seconds: float) -> None:
        self.store[key] = value

    async def invalidate(self, key: str) -> None:
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_tiered_cache_reads_from_l2_and_warms_l1() -> None:
    l1 = InMemoryCacheService()
    l2 = _FakeRedisL2()
    l2.store["key"] = {"value": 1}
    cache = TieredCacheService(l1, l2)

    assert await cache.get("key") == {"value": 1}
    assert await l1.get("key") == {"value": 1}


@pytest.mark.asyncio
async def test_tiered_cache_writes_both_layers() -> None:
    l1 = InMemoryCacheService()
    l2 = _FakeRedisL2()
    cache = TieredCacheService(l1, l2, l2_min_ttl_seconds=60.0)

    await cache.set("key", {"value": 2}, ttl_seconds=5.0)
    assert await l1.get("key") == {"value": 2}
    assert l2.store["key"] == {"value": 2}


@pytest.mark.asyncio
async def test_build_cache_service_memory_only_without_redis_url() -> None:
    reset_cache_service()
    settings = Settings(_env_file=None, REDIS_URL="")
    service = build_cache_service(settings)
    assert isinstance(service, InMemoryCacheService)


@pytest.mark.asyncio
async def test_build_cache_service_tiered_when_redis_url_set() -> None:
    reset_cache_service()
    settings = Settings(_env_file=None, REDIS_URL="redis://localhost:6379/0")
    service = build_cache_service(settings)
    assert isinstance(service, TieredCacheService)


@pytest.mark.asyncio
async def test_redis_cache_degrades_when_unavailable() -> None:
    cache = RedisCacheService("redis://127.0.0.1:1")
    assert await cache.get("missing") is None
    await cache.set("missing", {"x": 1}, ttl_seconds=5)
    assert cache.available is False
