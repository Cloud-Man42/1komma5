"""Simple in-memory rate limiter for admin connection tests."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimitStore:
    _hits: dict[str, float] = field(default_factory=dict)
    interval_seconds: float = 5.0

    def check(self, key: str) -> bool:
        now = time.monotonic()
        last = self._hits.get(key)
        if last is not None and now - last < self.interval_seconds:
            return False
        self._hits[key] = now
        return True


connection_test_rate_limiter = RateLimitStore()
