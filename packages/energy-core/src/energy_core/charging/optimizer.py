"""EV smart charging optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.charging.config import ChargingConfig
from energy_core.charging.models import ChargingDecision
from energy_core.charging.policy import (
    PRICE_MODES,
    normalized_mode,
    respects_manual_pause,
    uses_price_optimization,
)
from energy_core.charging.power_to_current import power_to_current_a
from energy_core.charging.smart_schedule import (
    price_allows_immediate_grid_charge,
    resolve_schedule_mode,
    should_charge_by_price,
    should_charge_smart,
)
from energy_core.energy.state import EnergyState
from energy_core.solar_forecast.types import SolarChargingPlan


@dataclass
class SolarDelayState:
    export_above_start_since: datetime | None = None
    export_below_stop_since: datetime | None = None


@dataclass(frozen=True, slots=True)
class OptimizerTarget:
    target_current_a: float
    reason: str


# Remaining time below smart_charge_hours counts as fully urgent; above
# DEADLINE_RELAXED_FACTOR times that there is room to wait for price and solar.
DEADLINE_RELAXED_FACTOR = 3.0
# Urgency where price rules are dropped so the deadline can still be met.
DEADLINE_RISK_URGENCY = 0.8
# Above this urgency, deferring grid charging for forecast solar is too risky.
SOLAR_DEFER_MAX_URGENCY = 0.5
PRICE_CHARGE_REASONS = frozenset(
    {"cheap_now", "smart_scheduled", "normal_price_ok", "smart_urgency_balanced"}
)


class EvChargingOptimizer:
    """Pure optimizer for SOL, SMART and deadline-aware charging targets."""

    def __init__(self) -> None:
        self._solar_state = SolarDelayState()

    def optimize(
        self,
        state: EnergyState,
        *,
        config: ChargingConfig,
        charging_mode: str,
        override_active: bool = False,
        now: datetime | None = None,
    ) -> ChargingDecision:
        now = now or datetime.now(UTC)
        mode = (charging_mode or state.heartbeat_charging_mode or "SMART_CHARGE").upper()
        target = self.optimize_target(
            state,
            config=config,
            charging_mode=mode,
            override_active=override_active,
            now=now,
        )
        return _target_to_decision(target, mode, config)

    def optimize_target(
        self,
        state: EnergyState,
        *,
        config: ChargingConfig,
        charging_mode: str,
        override_active: bool = False,
        now: datetime | None = None,
        solar_plan: SolarChargingPlan | None = None,
    ) -> OptimizerTarget:
        now = now or datetime.now(UTC)
        mode = normalized_mode(charging_mode or state.heartbeat_charging_mode)

        if state.stale:
            return OptimizerTarget(0.0, "stale_data")

        if respects_manual_pause(mode, override_active=override_active):
            return OptimizerTarget(0.0, "user_paused")

        if override_active:
            return OptimizerTarget(_max_current(config), "override")

        if mode in {"QUICK_CHARGE", "QUICK"}:
            return OptimizerTarget(_max_current(config), "quick_charge")

        if _battery_blocks_ev(state, config):
            return OptimizerTarget(0.0, "battery_priority")

        if mode in {"SOLAR_CHARGE", "SOLAR"}:
            return self._optimize_solar_target(state, config, now=now, mode=mode)

        if normalized_mode(mode) in PRICE_MODES:
            return self._optimize_price_target(state, config, now=now, mode=mode)

        if uses_price_optimization(mode, override_active=False) or state.heartbeat_smart_charge_active:
            return self._optimize_smart_target(
                state, config, now=now, mode=mode, solar_plan=solar_plan
            )

        if state.ev_charge_from_grid_recommended:
            return OptimizerTarget(_max_current(config), "cheap_grid_charge")

        return OptimizerTarget(0.0, "no_signal")

    def _optimize_solar_target(
        self,
        state: EnergyState,
        config: ChargingConfig,
        *,
        now: datetime,
        mode: str,
    ) -> OptimizerTarget:
        export_w = _effective_export_w(state)
        if state.grid_import_w is not None and state.grid_import_w > config.grid_deadband_w:
            self._reset_solar_delays()
            return OptimizerTarget(0.0, "grid_import")

        if export_w >= config.solar_start_threshold_w:
            if self._solar_state.export_above_start_since is None:
                self._solar_state.export_above_start_since = now
            self._solar_state.export_below_stop_since = None
            if (now - self._solar_state.export_above_start_since).total_seconds() < config.solar_start_delay_seconds:
                return OptimizerTarget(0.0, "solar_start_delay")
        elif export_w <= config.solar_stop_threshold_w:
            self._solar_state.export_above_start_since = None
            if self._solar_state.export_below_stop_since is None:
                self._solar_state.export_below_stop_since = now
            if (now - self._solar_state.export_below_stop_since).total_seconds() >= config.solar_stop_delay_seconds:
                self._reset_solar_delays()
                return OptimizerTarget(0.0, "insufficient_export")
            return OptimizerTarget(0.0, "solar_stop_delay")
        else:
            self._solar_state.export_above_start_since = None
            self._solar_state.export_below_stop_since = None
            return OptimizerTarget(0.0, "export_hysteresis")

        current = power_to_current_a(
            export_w,
            phases=config.phases,
            nominal_voltage_v=config.nominal_voltage_v,
            min_current_a=config.min_current_a,
            max_current_a=config.max_current_a,
            max_power_w=config.max_power_w,
        )
        current = _clamp_current(current, config)
        if current <= 0:
            return OptimizerTarget(0.0, "insufficient_export")
        return OptimizerTarget(current, "stable_grid_export")

    def _optimize_price_target(
        self,
        state: EnergyState,
        config: ChargingConfig,
        *,
        now: datetime,
        mode: str,
    ) -> OptimizerTarget:
        if _battery_blocks_ev(state, config):
            return OptimizerTarget(0.0, "battery_priority")

        charge, reason = should_charge_by_price(
            now,
            price_forecast=state.price_forecast,
            current_price=state.electricity_price_eur_kwh,
            expensive_threshold=config.expensive_price_eur_kwh,
            charge_hours=config.smart_charge_hours,
        )
        if charge:
            return OptimizerTarget(_max_current(config), reason)
        return OptimizerTarget(0.0, reason)

    def _optimize_smart_target(
        self,
        state: EnergyState,
        config: ChargingConfig,
        *,
        now: datetime,
        mode: str,
        solar_plan: SolarChargingPlan | None = None,
    ) -> OptimizerTarget:
        deadline = config.deadline_at or _deadline_from_departure(
            now, config.departure_time or state.departure_time, config.timezone
        )
        urgency = charging_urgency(now, deadline=deadline, config=config)

        if deadline is not None and deadline <= now:
            return OptimizerTarget(_max_current(config), "deadline_overdue")
        if urgency >= DEADLINE_RISK_URGENCY:
            return OptimizerTarget(_max_current(config), "deadline_risk")

        export_w = _effective_export_w(state)
        if export_w >= config.solar_start_threshold_w:
            current = power_to_current_a(
                export_w,
                phases=config.phases,
                nominal_voltage_v=config.nominal_voltage_v,
                min_current_a=config.min_current_a,
                max_current_a=config.max_current_a,
                max_power_w=config.max_power_w,
            )
            current = _clamp_current(current, config)
            if current > 0:
                return OptimizerTarget(current, "smart_solar_surplus")

        if _should_wait_for_solar_forecast(
            solar_plan,
            urgency=urgency,
            state=state,
            config=config,
            now=now,
        ):
            return OptimizerTarget(0.0, "solar_forecast_wait")

        schedule_mode = resolve_schedule_mode(
            departure_time=config.departure_time or state.departure_time,
            deadline_at=config.deadline_at,
        )
        charge, reason = should_charge_smart(
            now,
            departure_time=config.departure_time or state.departure_time,
            price_forecast=state.price_forecast,
            current_price=state.electricity_price_eur_kwh,
            expensive_threshold=config.expensive_price_eur_kwh,
            charge_hours=config.smart_charge_hours,
            timezone=config.timezone,
            schedule_mode=schedule_mode,
            urgency=urgency,
        )
        grid_needed = solar_plan is not None and not solar_plan.solar_first
        if charge:
            if grid_needed and reason in PRICE_CHARGE_REASONS:
                return OptimizerTarget(_max_current(config), "solar_forecast_partial_grid")
            return OptimizerTarget(_max_current(config), reason)
        if grid_needed:
            return OptimizerTarget(0.0, "solar_forecast_wait_cheaper")
        return OptimizerTarget(0.0, reason)

    def _reset_solar_delays(self) -> None:
        self._solar_state.export_above_start_since = None
        self._solar_state.export_below_stop_since = None


def _effective_export_w(state: EnergyState) -> float:
    if state.grid_export_w is not None:
        export = max(0.0, state.grid_export_w)
        discharge = state.battery_discharge_power_w or 0.0
        return max(0.0, export - discharge)
    pv = state.pv_power_w or 0.0
    home = state.home_consumption_w or 0.0
    battery_charge = state.battery_charge_power_w
    if battery_charge is None and state.battery_power_w is not None:
        battery_charge = max(0.0, state.battery_power_w)
    return max(0.0, pv - home - (battery_charge or 0.0))


def _battery_blocks_ev(state: EnergyState, config: ChargingConfig) -> bool:
    soc = state.battery_soc
    power = state.battery_power_w
    if soc is None or power is None:
        return False
    return soc < config.battery_low_soc_threshold and power > config.battery_charge_power_threshold_w


def charging_urgency(
    now: datetime,
    *,
    deadline: datetime | None,
    config: ChargingConfig,
) -> float:
    """Rise from 0 to 1 as the time left before the deadline shrinks."""
    if deadline is None:
        return 0.0
    if deadline <= now:
        return 1.0
    hours_left = (deadline - now).total_seconds() / 3600.0
    urgent_hours = max(0.5, config.smart_charge_hours)
    relaxed_hours = urgent_hours * DEADLINE_RELAXED_FACTOR
    if hours_left <= urgent_hours:
        return 1.0
    if hours_left >= relaxed_hours:
        return 0.0
    return (relaxed_hours - hours_left) / (relaxed_hours - urgent_hours)


def _should_wait_for_solar_forecast(
    solar_plan: SolarChargingPlan | None,
    *,
    urgency: float,
    state: EnergyState,
    config: ChargingConfig,
    now: datetime,
) -> bool:
    if solar_plan is None or not solar_plan.solar_first:
        return False
    if urgency >= SOLAR_DEFER_MAX_URGENCY:
        return False
    return not price_allows_immediate_grid_charge(
        state.electricity_price_eur_kwh,
        state.price_forecast,
        expensive_threshold=config.expensive_price_eur_kwh,
        now=now,
    )


def _deadline_from_departure(now: datetime, departure_time: str | None, timezone: str) -> datetime | None:
    if not departure_time:
        return None
    try:
        hour, minute = map(int, departure_time.split(":"))
        tz = ZoneInfo(timezone)
        local_now = now.astimezone(tz)
        departure = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if departure <= local_now:
            departure += timedelta(days=1)
        return departure.astimezone(UTC)
    except (ValueError, KeyError):
        return None


def _max_current(config: ChargingConfig) -> float:
    return max(0.0, config.max_current_a)


def _clamp_current(current: float, config: ChargingConfig) -> float:
    if current <= 0:
        return 0.0
    current = min(current, config.max_current_a)
    if current < config.min_current_a:
        return 0.0
    return current


def _power_for_current(current_a: float, config: ChargingConfig) -> float:
    if current_a <= 0:
        return 0.0
    import math

    if config.phases >= 3:
        return current_a * math.sqrt(3) * config.nominal_voltage_v
    return current_a * config.nominal_voltage_v


def _target_to_decision(target: OptimizerTarget, mode: str, config: ChargingConfig) -> ChargingDecision:
    if target.reason == "stale_data":
        return _decision("NONE", 0.0, None, target.reason, mode, skip_apply=True)
    if target.target_current_a <= 0:
        return _decision("STOP", 0.0, None, target.reason, mode)
    return _decision(
        "SET_CURRENT",
        target.target_current_a,
        _power_for_current(target.target_current_a, config),
        target.reason,
        mode,
    )


def _decision(
    action: str,
    current_a: float,
    power_w: float | None,
    reason: str,
    mode: str,
    *,
    skip_apply: bool = False,
) -> ChargingDecision:
    action_map = {
        "START": "set_current",
        "STOP": "stop",
        "SET_CURRENT": "set_current",
        "NONE": "none",
    }
    normalized_action = action_map.get(action, action.lower())
    if normalized_action == "stop":
        current_a = 0.0
    return ChargingDecision(
        requested_current_a=current_a,
        applied_current_a=current_a,
        requested_power_w=power_w,
        action=normalized_action,
        reason=reason,
        policy_mode=mode,
        skip_apply=skip_apply,
    )
