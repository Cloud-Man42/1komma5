"""Normalized energy optimization events (vendor-neutral)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def parse_active_optimizations(items: list[dict[str, Any]] | None, *, now: datetime | None = None) -> tuple[str, ...]:
    if not items:
        return ()
    now = now or datetime.now(UTC)
    active: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("type") or item.get("eventType") or "UNKNOWN")
        start = _parse_dt(item.get("start") or item.get("from") or item.get("startTime"))
        end = _parse_dt(item.get("end") or item.get("to") or item.get("endTime"))
        if start and end:
            if start <= now <= end:
                active.append(event_type)
        elif start and start <= now:
            active.append(event_type)
        elif start is None and end is None:
            active.append(event_type)
    return tuple(active)


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
