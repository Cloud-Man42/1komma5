"""DST-safe 15-minute period grid helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from energy_core.price_engine.types import INTERVAL_MINUTES


def align_period_start(ts: datetime, *, interval_minutes: int = INTERVAL_MINUTES) -> datetime:
    """Floor a timestamp to the start of its interval in UTC."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    else:
        ts = ts.astimezone(UTC)
    minute = (ts.minute // interval_minutes) * interval_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)


def period_end(period_start: datetime, *, interval_minutes: int = INTERVAL_MINUTES) -> datetime:
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=UTC)
    return period_start + timedelta(minutes=interval_minutes)


def local_day_bounds(
    day: date,
    timezone: str,
) -> tuple[datetime, datetime]:
    """Return UTC bounds for a local calendar day (handles DST)."""
    tz = ZoneInfo(timezone)
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def local_today(timezone: str, *, now: datetime | None = None) -> date:
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    return ref.astimezone(ZoneInfo(timezone)).date()


def enumerate_periods(
    start: datetime,
    end: datetime,
    *,
    interval_minutes: int = INTERVAL_MINUTES,
) -> tuple[datetime, ...]:
    """Enumerate 15-minute period starts in [start, end)."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    else:
        start = start.astimezone(UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    else:
        end = end.astimezone(UTC)

    cursor = align_period_start(start, interval_minutes=interval_minutes)
    if cursor < start:
        cursor += timedelta(minutes=interval_minutes)

    periods: list[datetime] = []
    while cursor < end:
        periods.append(cursor)
        cursor += timedelta(minutes=interval_minutes)
    return tuple(periods)


def enumerate_local_day_periods(
    day: date,
    timezone: str,
    *,
    interval_minutes: int = INTERVAL_MINUTES,
) -> tuple[datetime, ...]:
    """All period starts for a local day; count varies on DST transitions."""
    day_start, day_end = local_day_bounds(day, timezone)
    return enumerate_periods(day_start, day_end, interval_minutes=interval_minutes)


def current_period_start(
    *,
    timezone: str,
    now: datetime | None = None,
    interval_minutes: int = INTERVAL_MINUTES,
) -> datetime:
    ref = now or datetime.now(UTC)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    return align_period_start(ref, interval_minutes=interval_minutes)
