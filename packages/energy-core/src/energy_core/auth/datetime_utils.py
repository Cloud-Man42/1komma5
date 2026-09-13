"""UTC datetime helpers for auth (SQLite returns naive timestamps)."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def utc_now() -> datetime:
    return datetime.now(UTC)
