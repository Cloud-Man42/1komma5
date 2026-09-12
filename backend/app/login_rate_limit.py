"""Rate limiter for login endpoint."""

from __future__ import annotations

import time
from collections import defaultdict, deque


class LoginRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit_per_minute: int) -> bool:
        now = time.monotonic()
        window = self._windows[key]
        cutoff = now - 60.0
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit_per_minute:
            return False
        window.append(now)
        return True


LOGIN_RATE_LIMITER = LoginRateLimiter()
