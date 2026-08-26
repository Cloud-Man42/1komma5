"""Track planned vs actual Arctic Spa filter cycles for a local day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from energy_core.flexible_load.types import PlanWindow
from energy_core.spa_energy.requirement import CLEANING_STATUSES


class FilterCycleState(StrEnum):
    SCHEDULED = "Scheduled"
    STARTED = "Started"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    SKIPPED = "Skipped"
    MANUAL = "Manual"
    PARTIAL = "Partial"


@dataclass(frozen=True, slots=True)
class FilterCycleRecord:
    cycle_index: int
    planned_start: datetime
    planned_end: datetime
    state: FilterCycleState
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    runtime_minutes: float = 0.0
    manual: bool = False

    @property
    def planned_duration_minutes(self) -> float:
        return (self.planned_end - self.planned_start).total_seconds() / 60.0

    @property
    def completion_ratio(self) -> float:
        required = self.planned_duration_minutes
        if required <= 0:
            return 0.0
        return min(1.0, self.runtime_minutes / required)


def _cleaning_segments(
    samples: list[tuple[datetime, str | None]],
    *,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[datetime, datetime, float]]:
    if not samples:
        return []

    sorted_samples = sorted(samples, key=lambda x: x[0])
    segments: list[tuple[datetime, datetime, float]] = []
    in_cleaning = False
    segment_start: datetime | None = None

    for ts, status in sorted_samples:
        if ts < day_start:
            in_cleaning = status in CLEANING_STATUSES
            if in_cleaning:
                segment_start = day_start
            continue
        if ts > day_end:
            break

        active = status in CLEANING_STATUSES
        if active and not in_cleaning:
            in_cleaning = True
            segment_start = ts
        elif not active and in_cleaning and segment_start is not None:
            end = ts
            start = max(segment_start, day_start)
            minutes = max(0.0, (end - start).total_seconds() / 60.0)
            if minutes > 0:
                segments.append((start, end, minutes))
            in_cleaning = False
            segment_start = None

    if in_cleaning and segment_start is not None:
        end = min(day_end, sorted_samples[-1][0])
        start = max(segment_start, day_start)
        minutes = max(0.0, (end - start).total_seconds() / 60.0)
        if minutes > 0:
            segments.append((start, end, minutes))

    return segments


def _overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0.0
    return (end - start).total_seconds() / 60.0


def reconcile_filter_cycles(
    planned_windows: tuple[PlanWindow, ...],
    samples: list[tuple[datetime, str | None]],
    *,
    day_start: datetime,
    day_end: datetime,
    required_duration_minutes: int,
    now: datetime,
    completion_threshold: float = 0.95,
) -> tuple[FilterCycleRecord, ...]:
    """Match actual filter runs to planned 2 h cycles."""
    segments = _cleaning_segments(samples, day_start=day_start, day_end=day_end)
    records: list[FilterCycleRecord] = []

    for index, window in enumerate(planned_windows):
        runtime = 0.0
        actual_start: datetime | None = None
        actual_end: datetime | None = None
        for seg_start, seg_end, minutes in segments:
            overlap = _overlap_minutes(window.start, window.end, seg_start, seg_end)
            if overlap <= 0:
                continue
            runtime += overlap
            actual_start = seg_start if actual_start is None else min(actual_start, seg_start)
            actual_end = seg_end if actual_end is None else max(actual_end, seg_end)

        required = float(required_duration_minutes)
        state = FilterCycleState.SCHEDULED
        if window.end <= now and runtime <= 0:
            state = FilterCycleState.SKIPPED
        elif runtime >= required * completion_threshold:
            state = FilterCycleState.COMPLETED
        elif runtime > 0 and runtime < required * completion_threshold:
            state = FilterCycleState.PARTIAL
        elif window.start <= now < window.end and runtime > 0:
            state = FilterCycleState.RUNNING
        elif window.start <= now < window.end:
            state = FilterCycleState.STARTED
        elif window.start > now:
            state = FilterCycleState.SCHEDULED

        records.append(
            FilterCycleRecord(
                cycle_index=index + 1,
                planned_start=window.start,
                planned_end=window.end,
                state=state,
                actual_start=actual_start,
                actual_end=actual_end,
                runtime_minutes=round(runtime, 1),
            )
        )

    return tuple(records)


def count_completed_cycles(records: tuple[FilterCycleRecord, ...]) -> int:
    return sum(1 for r in records if r.state in {FilterCycleState.COMPLETED, FilterCycleState.MANUAL})


def remaining_cycles(records: tuple[FilterCycleRecord, ...]) -> int:
    return sum(
        1
        for r in records
        if r.state
        in {
            FilterCycleState.SCHEDULED,
            FilterCycleState.STARTED,
            FilterCycleState.PARTIAL,
            FilterCycleState.FAILED,
        }
    )


def next_upcoming_window(
    planned_windows: tuple[PlanWindow, ...],
    now: datetime,
) -> PlanWindow | None:
    upcoming = [w for w in planned_windows if w.end > now]
    if not upcoming:
        return None
    return min(upcoming, key=lambda w: w.start)


def minutes_until(window: PlanWindow, now: datetime) -> int:
    if now >= window.start:
        return 0
    return max(0, int((window.start - now).total_seconds() // 60))
