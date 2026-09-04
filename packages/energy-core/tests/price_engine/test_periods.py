"""Tests for DST-safe 15-minute period grid."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.price_engine.periods import (
    align_period_start,
    enumerate_local_day_periods,
    enumerate_periods,
    local_day_bounds,
)


def test_align_period_start_floors_to_quarter_hour():
    ts = datetime(2026, 3, 15, 13, 37, 42, tzinfo=UTC)
    assert align_period_start(ts) == datetime(2026, 3, 15, 13, 30, tzinfo=UTC)


def test_stockholm_spring_dst_day_has_92_periods():
    # Last Sunday in March 2026 — clocks forward 02:00 -> 03:00
    day = date(2026, 3, 29)
    periods = enumerate_local_day_periods(day, "Europe/Stockholm")
    assert len(periods) == 92


def test_stockholm_fall_dst_day_has_100_periods():
    # Last Sunday in October 2026 — clocks back 03:00 -> 02:00
    day = date(2026, 10, 25)
    periods = enumerate_local_day_periods(day, "Europe/Stockholm")
    assert len(periods) == 100


def test_normal_day_has_96_periods():
    day = date(2026, 6, 15)
    periods = enumerate_local_day_periods(day, "Europe/Stockholm")
    assert len(periods) == 96


def test_copenhagen_dst_same_rules():
    spring = enumerate_local_day_periods(date(2026, 3, 29), "Europe/Copenhagen")
    assert len(spring) == 92


def test_local_day_bounds_respect_timezone():
    day = date(2026, 8, 13)
    start, end = local_day_bounds(day, "Europe/Stockholm")
    tz = ZoneInfo("Europe/Stockholm")
    assert start.astimezone(tz).date() == day
    assert end.astimezone(tz).date() == day + timedelta(days=1)


def test_enumerate_periods_half_open_interval():
    start = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    end = datetime(2026, 8, 13, 11, 0, tzinfo=UTC)
    periods = enumerate_periods(start, end)
    assert periods == (
        datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 30, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 45, tzinfo=UTC),
    )
