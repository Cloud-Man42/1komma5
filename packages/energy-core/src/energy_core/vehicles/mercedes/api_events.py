"""In-memory ring buffer for Mercedes API events (no secrets)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class MercedesApiEvent:
    endpoint: str
    method: str
    http_status: int | None
    duration_ms: int
    error_code: str | None
    retry_count: int
    recorded_at: datetime


class MercedesApiEventBuffer:
    def __init__(self, *, max_size: int = 50) -> None:
        self._max_size = max_size
        self._events: deque[MercedesApiEvent] = deque(maxlen=max_size)

    def record(
        self,
        *,
        endpoint: str,
        method: str,
        http_status: int | None,
        duration_ms: int,
        error_code: str | None = None,
        retry_count: int = 0,
    ) -> None:
        self._events.append(
            MercedesApiEvent(
                endpoint=endpoint,
                method=method,
                http_status=http_status,
                duration_ms=duration_ms,
                error_code=error_code,
                retry_count=retry_count,
                recorded_at=datetime.now(UTC),
            )
        )

    def list_recent(self, *, limit: int | None = None) -> list[MercedesApiEvent]:
        items = list(self._events)
        if limit is not None:
            return items[-limit:]
        return items

    def clear(self) -> None:
        self._events.clear()
