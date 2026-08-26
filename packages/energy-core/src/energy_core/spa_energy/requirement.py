"""Derive spa cleaning requirements from status and history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


CLEANING_STATUSES = frozenset({"Filtering", "Purge", "Sanitize", "Boost"})


@dataclass(frozen=True, slots=True)
class SpaCleaningRequirement:
    minimum_runtime_hours: float
    maximum_runtime_hours: float
    cleaning_deadline: datetime
    last_cleaning_end: datetime | None
    hours_since_last_cleaning: float | None
    hours_required_within_24h: float
    filter_frequency_per_day: float
    filter_duration_hours: float


def parse_local_time(hhmm: str, reference: datetime, timezone: str) -> datetime:
    tz = ZoneInfo(timezone)
    local = reference.astimezone(tz)
    hour, minute = (int(x) for x in hhmm.split(":"))
    candidate = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


def window_bounds(
    reference: datetime,
    *,
    timezone: str,
    start_hhmm: str,
    end_hhmm: str,
) -> tuple[datetime, datetime]:
    tz = ZoneInfo(timezone)
    local = reference.astimezone(tz)
    sh, sm = (int(x) for x in start_hhmm.split(":"))
    eh, em = (int(x) for x in end_hhmm.split(":"))
    earliest = local.replace(hour=sh, minute=sm, second=0, microsecond=0)
    latest = local.replace(hour=eh, minute=em, second=0, microsecond=0)
    if latest <= earliest:
        latest += timedelta(days=1)
    if earliest < local:
        earliest = local
    return earliest.astimezone(UTC), latest.astimezone(UTC)


def detect_last_cleaning_end(
    samples: list[tuple[datetime, str | None]],
) -> datetime | None:
    """Find end of most recent cleaning run from filter_status samples."""
    if not samples:
        return None
    sorted_samples = sorted(samples, key=lambda x: x[0])
    in_cleaning = False
    last_end: datetime | None = None
    for ts, status in sorted_samples:
        active = status in CLEANING_STATUSES
        if active and not in_cleaning:
            in_cleaning = True
        elif not active and in_cleaning:
            last_end = ts
            in_cleaning = False
    if in_cleaning:
        last_end = sorted_samples[-1][0]
    return last_end


def build_cleaning_requirement(
    *,
    now: datetime,
    filter_frequency_per_day: float,
    filter_duration_hours: float,
    min_cleaning_hours_per_day: float,
    last_cleaning_end: datetime | None,
    timezone: str,
    allowed_window_end_hhmm: str,
) -> SpaCleaningRequirement:
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    freq = max(filter_frequency_per_day, min_cleaning_hours_per_day / max(filter_duration_hours, 0.5))
    duration = max(filter_duration_hours, min_cleaning_hours_per_day)

    hours_since: float | None = None
    if last_cleaning_end is not None:
        hours_since = (now - last_cleaning_end).total_seconds() / 3600.0

    interval_hours = 24.0 / max(freq, 0.1)
    if hours_since is not None:
        deadline = last_cleaning_end + timedelta(hours=interval_hours)  # type: ignore[operator]
    else:
        deadline = now + timedelta(hours=interval_hours)

    _, latest_finish = window_bounds(
        now,
        timezone=timezone,
        start_hhmm="00:00",
        end_hhmm=allowed_window_end_hhmm,
    )
    if deadline > latest_finish:
        deadline = latest_finish

    required = min_cleaning_hours_per_day
    min_runtime_hours = min(duration, min_cleaning_hours_per_day)
    max_runtime_hours = min_cleaning_hours_per_day
    return SpaCleaningRequirement(
        minimum_runtime_hours=min_runtime_hours,
        maximum_runtime_hours=max_runtime_hours,
        cleaning_deadline=deadline,
        last_cleaning_end=last_cleaning_end,
        hours_since_last_cleaning=hours_since,
        hours_required_within_24h=required,
        filter_frequency_per_day=freq,
        filter_duration_hours=duration,
    )
