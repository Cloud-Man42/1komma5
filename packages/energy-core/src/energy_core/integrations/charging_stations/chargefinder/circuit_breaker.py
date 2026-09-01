"""ChargeFinder circuit breaker for blocked/degraded states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class ChargeFinderCircuitBreaker:
    blocked_until: datetime | None = None
    parser_failures: int = 0
    consecutive_http_blocks: int = 0

    def is_open(self) -> bool:
        if self.blocked_until is None:
            return False
        return datetime.now(UTC) < _aware(self.blocked_until)

    def record_success(self) -> None:
        self.blocked_until = None
        self.parser_failures = 0
        self.consecutive_http_blocks = 0

    def record_http_block(self, *, status_code: int, cooldown_seconds: float) -> None:
        self.consecutive_http_blocks += 1
        if status_code in {403, 429} or self.consecutive_http_blocks >= 2:
            self.blocked_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)

    def record_parser_failure(self, *, max_failures: int, cooldown_seconds: float) -> None:
        self.parser_failures += 1
        if self.parser_failures >= max_failures:
            self.blocked_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)

    def record_captcha_detected(self, *, cooldown_seconds: float) -> None:
        self.blocked_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
