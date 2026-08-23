"""Compute smart charging savings from bridge cycle telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.charging.power_to_current import current_to_power_w
from energy_core.db.ev_bridge_cycle_repo import EvBridgeCycleRecord

SMART_SAVINGS_REASONS = frozenset(
    {
        "cheap_now",
        "smart_scheduled",
        "cheap_grid_charge",
        "auto_fallback_cheap_now",
        "auto_fallback_smart_scheduled",
        "auto_fallback_cheap_grid_charge",
    }
)

MAX_INTERVAL_HOURS = 6.0


@dataclass(frozen=True, slots=True)
class ChargingSavings:
    energy_kwh: float
    actual_cost_sek: float
    baseline_cost_sek: float
    savings_sek: float
    savings_pct: float
    savings_ore: int
    charging_intervals: int
    period_avg_price_kwh: float | None


def compute_charging_savings(
    cycles: list[EvBridgeCycleRecord],
    *,
    phases: int = 3,
    nominal_voltage_v: float = 230.0,
) -> ChargingSavings:
    if len(cycles) < 2:
        return _empty()

    period_prices = [cycle.price_kwh for cycle in cycles if cycle.price_kwh is not None]
    period_avg = sum(period_prices) / len(period_prices) if period_prices else None

    total_kwh = 0.0
    actual_cost = 0.0
    intervals = 0

    for previous, current in zip(cycles, cycles[1:]):
        interval = _charging_interval(
            previous, current, phases=phases, nominal_voltage_v=nominal_voltage_v
        )
        if interval is None:
            continue
        kwh, price = interval
        total_kwh += kwh
        actual_cost += kwh * price
        intervals += 1

    if total_kwh <= 0 or period_avg is None:
        return _empty(period_avg_price_kwh=period_avg)

    baseline_cost = total_kwh * period_avg
    savings_sek = baseline_cost - actual_cost
    savings_pct = (savings_sek / baseline_cost * 100.0) if baseline_cost > 0 else 0.0
    savings_ore = max(0, round(savings_sek * 100))

    return ChargingSavings(
        energy_kwh=round(total_kwh, 3),
        actual_cost_sek=round(actual_cost, 2),
        baseline_cost_sek=round(baseline_cost, 2),
        savings_sek=round(max(0.0, savings_sek), 2),
        savings_pct=round(max(0.0, savings_pct), 1),
        savings_ore=savings_ore,
        charging_intervals=intervals,
        period_avg_price_kwh=round(period_avg, 4),
    )


def _charging_interval(
    previous: EvBridgeCycleRecord,
    current: EvBridgeCycleRecord,
    *,
    phases: int,
    nominal_voltage_v: float,
) -> tuple[float, float] | None:
    if previous.override_active:
        return None
    if previous.applied_current_a <= 0:
        return None
    if previous.decision_reason not in SMART_SAVINGS_REASONS:
        return None

    dt_hours = (current.recorded_at - previous.recorded_at).total_seconds() / 3600.0
    if dt_hours <= 0 or dt_hours > MAX_INTERVAL_HOURS:
        return None

    price = previous.price_kwh or current.price_kwh
    if price is None:
        return None

    power_w = current_to_power_w(
        previous.applied_current_a,
        phases=phases,
        nominal_voltage_v=nominal_voltage_v,
    )
    kwh = power_w * dt_hours / 1000.0
    if kwh <= 0:
        return None
    return kwh, price


def _empty(*, period_avg_price_kwh: float | None = None) -> ChargingSavings:
    return ChargingSavings(
        energy_kwh=0.0,
        actual_cost_sek=0.0,
        baseline_cost_sek=0.0,
        savings_sek=0.0,
        savings_pct=0.0,
        savings_ore=0,
        charging_intervals=0,
        period_avg_price_kwh=period_avg_price_kwh,
    )
