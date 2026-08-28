"""Performance module tests."""

from __future__ import annotations

import asyncio

import pytest

from energy_core.cache.service import InMemoryCacheService
from energy_core.performance.context import PerformanceContext, get_performance_context, set_performance_context
from energy_core.performance.store import PerformanceStore, RequestMetric


@pytest.mark.asyncio
async def test_cache_single_flight() -> None:
    cache = InMemoryCacheService()
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return 42

    results = await asyncio.gather(
        cache.get_or_set("key", factory, ttl_seconds=5),
        cache.get_or_set("key", factory, ttl_seconds=5),
    )
    assert results == [42, 42]
    assert calls == 1


@pytest.mark.asyncio
async def test_cache_ttl_expiry() -> None:
    cache = InMemoryCacheService()
    await cache.set("key", "value", ttl_seconds=0.01)
    await asyncio.sleep(0.02)
    assert await cache.get("key") is None


def test_performance_context_tracks_db() -> None:
    ctx = PerformanceContext(request_id="abc", route="/test")
    set_performance_context(ctx)
    ctx.add_db_ms(12.5)
    ctx.add_db_ms(7.5)
    assert ctx.db_ms == 20.0
    assert ctx.query_count == 2
    assert get_performance_context() is ctx


def test_performance_store_route_stats() -> None:
    store = PerformanceStore(max_requests=100)
    for ms in [10, 20, 30, 40, 500]:
        store.record_request(
            RequestMetric(
                request_id="1",
                route="/api/sites/x/dashboard",
                total_ms=float(ms),
                db_ms=1,
                cache_ms=0,
                external_ms=0,
                calculation_ms=0,
                serialization_ms=0,
                query_count=1,
                response_bytes=100,
                cache_hit=False,
                site_id=1,
                timestamp=0,
            )
        )
    stats = store.route_stats(limit=5)
    assert stats[0]["route"] == "/api/sites/x/dashboard"
    assert stats[0]["p95_ms"] == 500
