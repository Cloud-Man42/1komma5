"""Seeded readings must land in the past whatever time of day the suite runs.

Hardcoded hours combined with today's date used to put readings in the future for
part of every day, which made the dashboard aggregate silently skip them.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import pairwise

from helpers import READING_SPACING, recent_reading_timestamps

DAY_START = datetime(2026, 8, 23, 0, 0, tzinfo=UTC)


def test_timestamps_end_at_now_with_the_requested_spacing():
    now = DAY_START + timedelta(hours=9)
    stamps = recent_reading_timestamps(now, DAY_START, 3)
    assert stamps == [
        now - 2 * READING_SPACING,
        now - READING_SPACING,
        now,
    ]


def test_timestamps_are_never_in_the_future():
    now = DAY_START + timedelta(hours=9)
    assert all(stamp <= now for stamp in recent_reading_timestamps(now, DAY_START, 5))


def test_spacing_shrinks_so_nothing_falls_into_yesterday():
    """Just after local midnight there is no room for the full interval."""
    now = DAY_START + timedelta(seconds=30)
    stamps = recent_reading_timestamps(now, DAY_START, 3)
    assert stamps[0] == DAY_START
    assert stamps[-1] == now
    assert all(DAY_START <= stamp <= now for stamp in stamps)


def test_gaps_stay_within_the_aggregation_window():
    """Gaps above five minutes are dropped by the daily aggregate."""
    now = DAY_START + timedelta(hours=9)
    stamps = recent_reading_timestamps(now, DAY_START, 4)
    gaps = [later - earlier for earlier, later in pairwise(stamps)]
    assert all(timedelta(0) < gap <= timedelta(minutes=5) for gap in gaps)


def test_single_sample_is_seeded_at_now():
    now = DAY_START + timedelta(hours=9)
    assert recent_reading_timestamps(now, DAY_START, 1) == [now]


def test_no_samples_produces_no_timestamps():
    assert recent_reading_timestamps(DAY_START, DAY_START, 0) == []
