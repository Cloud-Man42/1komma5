"""Persistent smart charging state machine — modulate first, stop last."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from energy_core.charging.config import ChargingConfig
from energy_core.charging.models import ChargingDecision
from energy_core.charging.policy import (
    bypasses_guardrails,
    decision_policy_mode,
    immediate_start,
    normalized_mode,
    respects_manual_pause,
    uses_start_delay,
)
from energy_core.charging.signal_filter import FilteredEnergySignals


class SmartChargingState(StrEnum):
    PAUSED = "PAUSED"
    WAITING_TO_START = "WAITING_TO_START"
    STARTING = "STARTING"
    CHARGING_STABLE = "CHARGING_STABLE"
    REDUCING = "REDUCING"
    WAITING_TO_STOP = "WAITING_TO_STOP"
    STOPPING = "STOPPING"
    COOLDOWN = "COOLDOWN"
    FAULT = "FAULT"


@dataclass
class SmartChargingRuntime:
    state: SmartChargingState = SmartChargingState.WAITING_TO_START
    requested_current_a: float = 0.0
    target_current_a: float = 0.0
    externally_limited: bool = False
    start_condition_since: datetime | None = None
    stop_condition_since: datetime | None = None
    temporary_import_since: datetime | None = None
    last_start_at: datetime | None = None
    last_stop_at: datetime | None = None
    last_requested_change_at: datetime | None = None
    automatic_starts: list[datetime] = field(default_factory=list)
    cooldown_until: datetime | None = None


def evaluate_smart_charging(
    *,
    runtime: SmartChargingRuntime,
    config: ChargingConfig,
    charging_mode: str,
    optimizer_target_a: float,
    optimizer_reason: str,
    slow_signals: FilteredEnergySignals,
    vehicle_connected: bool,
    halo_connected: bool,
    is_charging: bool,
    fault_code: str | None,
    now: datetime,
    override_active: bool = False,
) -> tuple[SmartChargingRuntime, ChargingDecision]:
    mode = normalized_mode(charging_mode)
    policy_mode = decision_policy_mode(charging_mode, override_active=override_active)
    fast_start = immediate_start(charging_mode, override_active=override_active)
    runtime.automatic_starts = _prune_starts(runtime.automatic_starts, now)

    if fault_code or not halo_connected:
        runtime.state = SmartChargingState.FAULT
        return runtime, _stop_decision(0.0, "fault", policy_mode, reason=fault_code or "charger_offline")

    if respects_manual_pause(charging_mode, override_active=override_active):
        runtime.state = SmartChargingState.PAUSED
        runtime.requested_current_a = 0.0
        runtime.target_current_a = 0.0
        return runtime, _stop_decision(0.0, "stop", policy_mode, reason="user_paused")

    if not vehicle_connected:
        runtime = _reset_timers(runtime)
        runtime.state = SmartChargingState.WAITING_TO_START
        runtime.requested_current_a = 0.0
        runtime.target_current_a = 0.0
        return runtime, _none_decision(0.0, policy_mode, reason="no_vehicle_connected")

    if (
        not bypasses_guardrails(charging_mode, override_active=override_active)
        and runtime.cooldown_until
        and now < runtime.cooldown_until
    ):
        runtime.state = SmartChargingState.COOLDOWN
        runtime.requested_current_a = 0.0
        runtime.target_current_a = 0.0
        return runtime, _none_decision(0.0, policy_mode, reason="cooldown")

    runtime.cooldown_until = None
    desired = _clamp_target(optimizer_target_a, config)
    export_w = max(0.0, slow_signals.grid_export_w - slow_signals.battery_discharge_power_w)
    import_w = slow_signals.grid_import_w
    in_run_period = _in_minimum_run_period(runtime, config, now)
    temporary_import_ok = _temporary_import_allowed(runtime, config, import_w, now)

    if desired <= 0:
        return _handle_stop_path(
            runtime=runtime,
            config=config,
            policy_mode=policy_mode,
            reason=optimizer_reason,
            import_w=import_w,
            in_run_period=in_run_period and not fast_start,
            temporary_import_ok=temporary_import_ok,
            is_charging=is_charging,
            fast_stop=fast_start,
            now=now,
        )

    if runtime.state in {
        SmartChargingState.WAITING_TO_START,
        SmartChargingState.COOLDOWN,
        SmartChargingState.STOPPING,
        SmartChargingState.PAUSED,
    }:
        return _handle_start_path(
            runtime=runtime,
            config=config,
            mode=mode,
            policy_mode=policy_mode,
            desired=desired,
            reason=optimizer_reason,
            export_w=export_w,
            override_active=override_active,
            now=now,
        )

    if runtime.requested_current_a <= 0 and desired > 0:
        return _handle_start_path(
            runtime=runtime,
            config=config,
            mode=mode,
            policy_mode=policy_mode,
            desired=desired,
            reason=optimizer_reason,
            export_w=export_w,
            override_active=override_active,
            now=now,
        )

    runtime.stop_condition_since = None
    next_current = _apply_ramp(runtime.requested_current_a, desired, config)
    if abs(next_current - runtime.requested_current_a) < 0.01:
        runtime.state = SmartChargingState.CHARGING_STABLE
        runtime.target_current_a = desired
        return runtime, _none_decision(runtime.requested_current_a, policy_mode, reason=optimizer_reason)

    if next_current < runtime.requested_current_a:
        runtime.state = SmartChargingState.REDUCING
    else:
        runtime.state = SmartChargingState.CHARGING_STABLE
    runtime.requested_current_a = next_current
    runtime.target_current_a = desired
    runtime.last_requested_change_at = now
    return runtime, _set_decision(next_current, policy_mode, reason=optimizer_reason)


def _handle_start_path(
    *,
    runtime: SmartChargingRuntime,
    config: ChargingConfig,
    mode: str,
    policy_mode: str,
    desired: float,
    reason: str,
    export_w: float,
    override_active: bool,
    now: datetime,
) -> tuple[SmartChargingRuntime, ChargingDecision]:
    fast_start = immediate_start(mode, override_active=override_active)

    if desired <= 0:
        runtime.state = SmartChargingState.WAITING_TO_START
        runtime.requested_current_a = 0.0
        runtime.target_current_a = 0.0
        return runtime, _none_decision(0.0, policy_mode, reason=reason)

    if not bypasses_guardrails(mode, override_active=override_active) and not _start_allowed(
        runtime, config, now
    ):
        runtime.state = SmartChargingState.WAITING_TO_START
        runtime.requested_current_a = 0.0
        runtime.target_current_a = desired
        return runtime, _none_decision(0.0, policy_mode, reason="start_rate_limited")

    if mode in {"SOLAR_CHARGE", "SOLAR"} and export_w < config.solar_start_threshold_w:
        runtime.start_condition_since = None
        runtime.state = SmartChargingState.WAITING_TO_START
        return runtime, _none_decision(0.0, policy_mode, reason="waiting_for_export")

    if uses_start_delay(mode, override_active=override_active):
        if runtime.start_condition_since is None:
            runtime.start_condition_since = now
        elapsed = (now - runtime.start_condition_since).total_seconds()
        if elapsed < config.start_delay_seconds:
            runtime.state = SmartChargingState.WAITING_TO_START
            return runtime, _none_decision(0.0, policy_mode, reason="start_delay")

    start_current = max(config.min_current_a, desired if fast_start else _apply_ramp(0.0, desired, config))
    runtime.state = SmartChargingState.CHARGING_STABLE if fast_start else SmartChargingState.STARTING
    runtime.requested_current_a = start_current
    runtime.target_current_a = desired
    runtime.last_requested_change_at = now
    runtime.last_start_at = now
    if not bypasses_guardrails(mode, override_active=override_active):
        runtime.automatic_starts.append(now)
    runtime.start_condition_since = None
    return runtime, _set_decision(start_current, policy_mode, reason=reason)


def _handle_stop_path(
    *,
    runtime: SmartChargingRuntime,
    config: ChargingConfig,
    policy_mode: str,
    reason: str,
    import_w: float,
    in_run_period: bool,
    temporary_import_ok: bool,
    is_charging: bool,
    fast_stop: bool,
    now: datetime,
) -> tuple[SmartChargingRuntime, ChargingDecision]:
    runtime.start_condition_since = None
    runtime.target_current_a = 0.0

    if not fast_stop and in_run_period and (temporary_import_ok or import_w <= config.grid_deadband_w):
        reduced = _apply_ramp(runtime.requested_current_a, config.min_current_a, config)
        if reduced >= config.min_current_a:
            runtime.state = SmartChargingState.REDUCING
            runtime.requested_current_a = reduced
            runtime.last_requested_change_at = now
            return runtime, _set_decision(reduced, policy_mode, reason="temporary_grid_import")

    if not fast_stop and in_run_period and runtime.requested_current_a > config.min_current_a:
        reduced = _apply_ramp(runtime.requested_current_a, config.min_current_a, config)
        runtime.state = SmartChargingState.REDUCING
        runtime.requested_current_a = reduced
        runtime.last_requested_change_at = now
        return runtime, _set_decision(reduced, policy_mode, reason="reduce_before_stop")

    stop_delay = 0.0 if fast_stop else config.stop_delay_seconds
    if runtime.stop_condition_since is None:
        runtime.stop_condition_since = now
    elapsed = (now - runtime.stop_condition_since).total_seconds()
    if elapsed < stop_delay and is_charging:
        runtime.state = SmartChargingState.WAITING_TO_STOP
        return runtime, _none_decision(runtime.requested_current_a, policy_mode, reason="stop_delay")

    runtime.state = SmartChargingState.STOPPING
    runtime.requested_current_a = 0.0
    runtime.last_stop_at = now
    if not fast_stop:
        runtime.cooldown_until = now + timedelta(seconds=config.minimum_off_time_seconds)
    runtime.stop_condition_since = None
    return runtime, _stop_decision(0.0, "stop", policy_mode, reason=reason)


def _temporary_import_allowed(
    runtime: SmartChargingRuntime,
    config: ChargingConfig,
    import_w: float,
    now: datetime,
) -> bool:
    if import_w <= config.temporary_grid_import_allowance_w:
        if runtime.temporary_import_since is None:
            runtime.temporary_import_since = now
        elapsed = (now - runtime.temporary_import_since).total_seconds()
        return elapsed <= config.temporary_grid_import_seconds
    runtime.temporary_import_since = None
    return False


def _in_minimum_run_period(runtime: SmartChargingRuntime, config: ChargingConfig, now: datetime) -> bool:
    if runtime.last_start_at is None:
        return False
    return (now - runtime.last_start_at).total_seconds() < config.minimum_run_time_seconds


def _start_allowed(runtime: SmartChargingRuntime, config: ChargingConfig, now: datetime) -> bool:
    if runtime.last_stop_at is not None:
        off_elapsed = (now - runtime.last_stop_at).total_seconds()
        if off_elapsed < config.minimum_off_time_seconds:
            return False
    return len(runtime.automatic_starts) < config.max_automatic_starts_per_hour


def _apply_ramp(current: float, target: float, config: ChargingConfig) -> float:
    if target > current:
        return min(target, current + config.max_current_increase_per_step_a)
    if target < current:
        return max(target, current - config.max_current_decrease_per_step_a)
    return current


def _clamp_target(target: float, config: ChargingConfig) -> float:
    if target <= 0:
        return 0.0
    target = min(target, config.max_current_a)
    if target < config.min_current_a:
        return 0.0
    return target


def _reset_timers(runtime: SmartChargingRuntime) -> SmartChargingRuntime:
    runtime.start_condition_since = None
    runtime.stop_condition_since = None
    runtime.temporary_import_since = None
    return runtime


def _prune_starts(starts: list[datetime], now: datetime) -> list[datetime]:
    cutoff = now - timedelta(hours=1)
    return [stamp for stamp in starts if stamp >= cutoff]


def restore_runtime_from_charger(
    *,
    smart_charging_state: str | None,
    last_requested_current_a: float | None,
    last_start_at: datetime | None,
    last_stop_at: datetime | None,
) -> SmartChargingRuntime:
    state = SmartChargingState.WAITING_TO_START
    if smart_charging_state:
        try:
            state = SmartChargingState(smart_charging_state)
        except ValueError:
            state = SmartChargingState.WAITING_TO_START
    return SmartChargingRuntime(
        state=state,
        requested_current_a=last_requested_current_a or 0.0,
        target_current_a=last_requested_current_a or 0.0,
        last_start_at=last_start_at,
        last_stop_at=last_stop_at,
    )


def _set_decision(current_a: float, mode: str, *, reason: str) -> ChargingDecision:
    return ChargingDecision(
        requested_current_a=current_a,
        applied_current_a=current_a,
        requested_power_w=None,
        action="set_current",
        reason=reason,
        policy_mode=mode,
    )


def _stop_decision(current_a: float, action: str, mode: str, *, reason: str) -> ChargingDecision:
    return ChargingDecision(
        requested_current_a=0.0,
        applied_current_a=0.0,
        requested_power_w=None,
        action=action,
        reason=reason,
        policy_mode=mode,
    )


def _none_decision(current_a: float, mode: str, *, reason: str) -> ChargingDecision:
    return ChargingDecision(
        requested_current_a=current_a,
        applied_current_a=current_a,
        requested_power_w=None,
        action="none",
        reason=reason,
        policy_mode=mode,
        skip_apply=True,
    )
