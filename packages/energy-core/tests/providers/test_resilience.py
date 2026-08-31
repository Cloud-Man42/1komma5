"""Tests for provider resilience helpers."""

from __future__ import annotations

import pytest

from energy_core.providers.resilience import CircuitBreaker, LastKnownGoodStore, resilient_call


@pytest.mark.asyncio
async def test_resilient_call_returns_last_known_good_on_failure() -> None:
    breaker = CircuitBreaker(failure_threshold=1)
    lkg = LastKnownGoodStore()
    lkg.set("test", {"ok": True})

    async def failing() -> dict:
        raise RuntimeError("upstream down")

    result = await resilient_call(
        breaker=breaker,
        lkg=lkg,
        key="test",
        call=failing,
        max_age_seconds=60.0,
    )
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_resilient_call_skips_caching_empty_payload() -> None:
    breaker = CircuitBreaker()
    lkg = LastKnownGoodStore()

    async def empty() -> dict:
        return {}

    result = await resilient_call(
        breaker=breaker,
        lkg=lkg,
        key="empty",
        call=empty,
        should_cache=lambda payload: isinstance(payload, dict) and bool(payload),
    )
    assert result == {}
    assert lkg.get("empty", max_age_seconds=60.0) is None

    breaker = CircuitBreaker(failure_threshold=1)
    lkg = LastKnownGoodStore()

    async def failing() -> dict:
        raise RuntimeError("upstream down")

    with pytest.raises(RuntimeError, match="upstream down"):
        await resilient_call(breaker=breaker, lkg=lkg, key="missing", call=failing)

    with pytest.raises(RuntimeError, match="Circuit open"):
        await resilient_call(breaker=breaker, lkg=lkg, key="missing", call=failing)
