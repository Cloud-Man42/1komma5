"""Reconnect backoff policy for Mercedes cloud access."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

BACKOFF_STEPS_SECONDS = (5, 15, 30, 60, 300, 900)


@dataclass(frozen=True, slots=True)
class BackoffDecision:
    delay_seconds: float
    attempt: int
    blocked: bool = False


class MercedesBackoffPolicy:
    def __init__(self) -> None:
        self._attempt = 0
        self._blocked = False

    def reset(self) -> None:
        self._attempt = 0
        self._blocked = False

    def on_success(self) -> None:
        self._attempt = 0
        self._blocked = False

    def on_rate_limited(self) -> BackoffDecision:
        self._blocked = True
        self._attempt = min(self._attempt + 1, len(BACKOFF_STEPS_SECONDS) - 1)
        delay = BACKOFF_STEPS_SECONDS[-1] + random.uniform(0, 30)
        return BackoffDecision(delay_seconds=delay, attempt=self._attempt, blocked=True)

    def on_failure(self) -> BackoffDecision:
        self._attempt = min(self._attempt + 1, len(BACKOFF_STEPS_SECONDS) - 1)
        base = BACKOFF_STEPS_SECONDS[self._attempt - 1] if self._attempt else BACKOFF_STEPS_SECONDS[0]
        delay = base + random.uniform(0, min(15, base * 0.2))
        return BackoffDecision(delay_seconds=delay, attempt=self._attempt, blocked=self._blocked)

    def backoff_until(self, decision: BackoffDecision) -> datetime:
        return datetime.now(UTC) + timedelta(seconds=decision.delay_seconds)
