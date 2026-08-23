"""Tests for smart charging state machine."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.config import ChargingConfig
from energy_core.charging.signal_filter import FilteredEnergySignals
from energy_core.charging.state_machine import (
    SmartChargingRuntime,
    SmartChargingState,
    evaluate_smart_charging,
)


def _config(**kwargs) -> ChargingConfig:
    defaults = {
        "max_current_a": 16.0,
        "min_current_a": 6.0,
        "start_delay_seconds": 120.0,
        "stop_delay_seconds": 300.0,
        "minimum_run_time_seconds": 300.0,
        "minimum_off_time_seconds": 300.0,
        "max_automatic_starts_per_hour": 4,
    }
    defaults.update(kwargs)
    return ChargingConfig(**defaults)


def _signals(**kwargs) -> FilteredEnergySignals:
    defaults = {
        "grid_import_w": 0.0,
        "grid_export_w": 5000.0,
        "pv_power_w": 5000.0,
        "home_consumption_w": 1000.0,
        "battery_charge_power_w": 0.0,
        "battery_discharge_power_w": 0.0,
    }
    defaults.update(kwargs)
    return FilteredEnergySignals(**defaults)


def test_paused_mode_stops_once():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        requested_current_a=12.0, state=SmartChargingState.CHARGING_STABLE
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(),
        charging_mode="PAUSED",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=True,
        fault_code=None,
        now=now,
    )
    assert runtime.state == SmartChargingState.PAUSED
    assert decision.action == "stop"
    assert decision.reason == "user_paused"


def test_start_requires_delay():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime()
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(start_delay_seconds=120.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "none"
    assert decision.reason == "start_delay"
    assert runtime.state == SmartChargingState.WAITING_TO_START


def test_urgent_reason_ramps_faster():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        requested_current_a=8.0,
        state=SmartChargingState.CHARGING_STABLE,
        last_start_at=now - timedelta(seconds=600),
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(max_current_increase_per_step_a=1.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="deadline_risk",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=True,
        fault_code=None,
        now=now,
    )
    assert decision.requested_current_a == 10.0


def test_normal_reason_ramps_one_amp_per_step():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        requested_current_a=8.0,
        state=SmartChargingState.CHARGING_STABLE,
        last_start_at=now - timedelta(seconds=600),
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(max_current_increase_per_step_a=1.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=True,
        fault_code=None,
        now=now,
    )
    assert decision.requested_current_a == 9.0


def test_solar_export_above_lowered_threshold_passes_gate():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime()
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(solar_start_threshold_w=1000.0),
        charging_mode="SOLAR_CHARGE",
        optimizer_target_a=8.0,
        optimizer_reason="stable_grid_export",
        slow_signals=_signals(grid_export_w=1200.0),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.reason != "waiting_for_export"
    assert decision.action == "set_current"


def test_solar_export_below_threshold_waits_for_export():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime()
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(solar_start_threshold_w=1000.0),
        charging_mode="SOLAR_CHARGE",
        optimizer_target_a=8.0,
        optimizer_reason="stable_grid_export",
        slow_signals=_signals(grid_export_w=700.0),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "none"
    assert decision.reason == "waiting_for_export"


def test_urgent_reason_skips_start_delay():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime()
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(start_delay_seconds=120.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="deadline_risk",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "set_current"
    assert decision.reason == "deadline_risk"
    assert runtime.state == SmartChargingState.STARTING


def test_start_after_delay():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(start_condition_since=now - timedelta(seconds=130))
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(start_delay_seconds=120.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "set_current"
    assert decision.requested_current_a >= 6.0
    assert runtime.state == SmartChargingState.STARTING


def test_stop_requires_delay_and_minimum_run():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        state=SmartChargingState.CHARGING_STABLE,
        requested_current_a=12.0,
        last_start_at=now - timedelta(seconds=60),
        stop_condition_since=now - timedelta(seconds=10),
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(stop_delay_seconds=300.0, minimum_run_time_seconds=300.0),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=0.0,
        optimizer_reason="smart_wait_cheaper",
        slow_signals=_signals(grid_import_w=2000.0, grid_export_w=0.0),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=True,
        fault_code=None,
        now=now,
    )
    assert decision.action in {"set_current", "none"}
    assert runtime.state in {SmartChargingState.REDUCING, SmartChargingState.WAITING_TO_STOP}


def test_cooldown_blocks_restart():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        cooldown_until=now + timedelta(seconds=120),
        state=SmartChargingState.COOLDOWN,
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "none"
    assert decision.reason == "cooldown"


def test_max_starts_per_hour():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(
        automatic_starts=[now - timedelta(minutes=m * 10) for m in range(4)],
        start_condition_since=now - timedelta(seconds=130),
    )
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(max_automatic_starts_per_hour=4),
        charging_mode="SMART_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="cheap_now",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.reason == "start_rate_limited"


def test_quick_charge_starts_immediately():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime()
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(start_delay_seconds=120.0),
        charging_mode="QUICK_CHARGE",
        optimizer_target_a=16.0,
        optimizer_reason="quick_charge",
        slow_signals=_signals(grid_import_w=5000.0, grid_export_w=0.0),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
    )
    assert decision.action == "set_current"
    assert decision.requested_current_a == 16.0
    assert decision.reason == "quick_charge"
    assert runtime.state == SmartChargingState.CHARGING_STABLE


def test_override_bypasses_paused_state():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    runtime = SmartChargingRuntime(state=SmartChargingState.PAUSED)
    runtime, decision = evaluate_smart_charging(
        runtime=runtime,
        config=_config(start_delay_seconds=120.0),
        charging_mode="PAUSED",
        optimizer_target_a=16.0,
        optimizer_reason="override",
        slow_signals=_signals(),
        vehicle_connected=True,
        halo_connected=True,
        is_charging=False,
        fault_code=None,
        now=now,
        override_active=True,
    )
    assert decision.action == "set_current"
    assert decision.policy_mode == "override"
    assert runtime.state == SmartChargingState.CHARGING_STABLE
