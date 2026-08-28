"""Provider resilience: circuit breaker and last-known-good cache."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    cooldown_seconds: float = 60.0
    _failures: int = 0
    _opened_at: float | None = None

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if time.monotonic() - self._opened_at >= self.cooldown_seconds:
            self._opened_at = None
            self._failures = 0
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()


@dataclass
class LastKnownGoodStore:
    _values: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def get(self, key: str, *, max_age_seconds: float) -> Any | None:
        entry = self._values.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > max_age_seconds:
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._values[key] = (time.monotonic(), value)


async def resilient_call(
    *,
    breaker: CircuitBreaker,
    lkg: LastKnownGoodStore,
    key: str,
    call: Callable[[], Any],
    max_age_seconds: float = 600.0,
) -> Any:
    if not breaker.allow():
        cached = lkg.get(key, max_age_seconds=max_age_seconds)
        if cached is not None:
            return cached
        raise RuntimeError(f"Circuit open for {key}")

    try:
        result = await call()
    except Exception:
        breaker.record_failure()
        cached = lkg.get(key, max_age_seconds=max_age_seconds)
        if cached is not None:
            return cached
        raise

    breaker.record_success()
    lkg.set(key, result)
    return result
