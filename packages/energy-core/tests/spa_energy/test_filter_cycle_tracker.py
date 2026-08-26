"""Tests for filter cycle state tracking."""

from datetime import UTC, datetime, timedelta

from energy_core.flexible_load.types import EnergySource, PlanWindow
from energy_core.spa_energy.filter_cycle_tracker import (
    FilterCycleState,
    count_completed_cycles,
    reconcile_filter_cycles,
    remaining_cycles,
)


def _window(start_h: int, end_h: int, day: datetime) -> PlanWindow:
    start = day.replace(hour=start_h, minute=0)
    end = day.replace(hour=end_h, minute=0)
    return PlanWindow(
        start=start,
        end=end,
        duration=end - start,
        expected_energy_kwh=1.0,
        expected_cost_sek=2.0,
        expected_energy_source=EnergySource.SOLAR,
        average_score=1.0,
        blocks=(),
    )


def test_partial_cycle_not_counted_completed():
    day = datetime(2026, 8, 26, tzinfo=UTC)
    windows = (_window(7, 9, day),)
    samples = [
        (day.replace(hour=7, minute=0), "Filtering"),
        (day.replace(hour=8, minute=24), "Idle"),
    ]
    records = reconcile_filter_cycles(
        windows,
        samples,
        day_start=day,
        day_end=day + timedelta(days=1),
        required_duration_minutes=120,
        now=day.replace(hour=12),
    )
    assert records[0].state == FilterCycleState.PARTIAL
    assert count_completed_cycles(records) == 0
    assert remaining_cycles(records) == 1


def test_completed_cycle_when_full_runtime():
    day = datetime(2026, 8, 26, tzinfo=UTC)
    windows = (_window(7, 9, day),)
    samples = [
        (day.replace(hour=7, minute=0), "Filtering"),
        (day.replace(hour=9, minute=5), "Idle"),
    ]
    records = reconcile_filter_cycles(
        windows,
        samples,
        day_start=day,
        day_end=day + timedelta(days=1),
        required_duration_minutes=120,
        now=day.replace(hour=12),
    )
    assert records[0].state == FilterCycleState.COMPLETED
    assert count_completed_cycles(records) == 1
