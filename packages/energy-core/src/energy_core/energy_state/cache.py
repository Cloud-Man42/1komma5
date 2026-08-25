"""In-process TTL cache for widget snapshots."""

from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class SnapshotCache(Generic[T]):
    """Simple monotonic-clock TTL cache keyed by site slug."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = max(0.0, ttl_seconds)
        self._entries: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        if self._ttl <= 0:
            return None
        entry = self._entries.get(key)
        if entry is None:
            return None
        cached_at, value = entry
        if time.monotonic() - cached_at > self._ttl:
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._entries[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._entries.clear()
