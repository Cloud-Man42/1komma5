"""Tests for spa planner watchdog."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from energy_core.db.spa_control_repo import SpaControlConfigRecord
from energy_core.spa_energy.runtime import SpaActuatorRuntime, SpaActuatorState
from energy_core.spa_energy.watchdog import SpaPlannerWatchdog


def _control(**kwargs) -> SpaControlConfigRecord:
    defaults = dict(
        consumer_id=1,
        smart_control_enabled=True,
        strategy="SMART",
        dry_run=False,
        shadow_mode=False,
        shadow_mode_until=None,
        min_cleaning_hours_per_day=2,
        allowed_window_start="07:00",
        allowed_window_end="22:00",
        prefer_solar=True,
        allow_battery=True,
        min_battery_soc_pct=40,
        min_run_minutes=30,
        min_stop_minutes=20,
        max_starts_per_day=4,
        filter_cycles_per_day=4,
        filter_duration_minutes=120,
        minimum_cycle_separation_minutes=60,
        filter_optimization_enabled=True,
        last_known_safe_filter_schedule_json=None,
        safety_floor_frequency_per_day=4,
        safety_floor_duration_hours=2,
        smart_preheat_enabled=False,
        normal_temperature_c=38,
        max_preheat_temperature_c=39,
        min_comfort_temperature_c=37,
        load_priority=50,
        fixed_schedule_start=None,
        fixed_schedule_end=None,
    )
    defaults.update(kwargs)
    return SpaControlConfigRecord(**defaults)


@pytest.mark.asyncio
async def test_watchdog_restores_safety_floor_when_planner_stale():
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    runtime = SpaActuatorRuntime(
        state=SpaActuatorState.IDLE,
        last_planner_run_at=now - timedelta(minutes=10),
    )
    control_service = AsyncMock()
    decision = await SpaPlannerWatchdog(stale_after_seconds=180).run(
        control=_control(),
        runtime=runtime,
        control_service=control_service,
        now=now,
        dry_run=False,
    )
    assert decision.command_sent is True
    control_service.ensure_safety_floor.assert_awaited_once()
    assert runtime.state == SpaActuatorState.DEGRADED


@pytest.mark.asyncio
async def test_watchdog_skips_when_planner_recent():
    now = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    runtime = SpaActuatorRuntime(
        state=SpaActuatorState.IDLE,
        last_planner_run_at=now - timedelta(seconds=30),
    )
    control_service = AsyncMock()
    decision = await SpaPlannerWatchdog(stale_after_seconds=180).run(
        control=_control(),
        runtime=runtime,
        control_service=control_service,
        now=now,
        dry_run=False,
    )
    assert decision.action == "none"
    control_service.ensure_safety_floor.assert_not_called()
