"""Tests for snapshot TTL cache."""

from energy_core.energy_state.cache import SnapshotCache


def test_snapshot_cache_hit_and_miss():
    cache = SnapshotCache[str](ttl_seconds=60.0)
    cache.set("akarp", "value")
    assert cache.get("akarp") == "value"
    assert cache.get("other") is None
    cache.clear()
    assert cache.get("akarp") is None
