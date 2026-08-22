"""Tests for smart charging savings calculation."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.savings import compute_charging_savings
from energy_core.db.ev_bridge_cycle_repo import EvBridgeCycleRecord


def _cycle(
    minutes: int,
    *,
    current: float,
    price: float,
    reason: str = "smart_scheduled",
) -> EvBridgeCycleRecord:
    base = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
    return EvBridgeCycleRecord(
        charger_id=1,
        recorded_at=base + timedelta(minutes=minutes),
        applied_current_a=current,
        price_kwh=price,
        policy_mode="derived",
        decision_reason=reason,
        override_active=False,
        vehicle_connected=True,
    )


def test_savings_empty_without_cycles():
    result = compute_charging_savings([])
    assert result.charging_intervals == 0
    assert result.savings_sek == 0.0


def test_savings_computes_cheaper_than_average():
    cycles = [
        _cycle(0, current=0.0, price=0.50, reason="smart_wait_cheaper"),
        _cycle(60, current=16.0, price=0.10, reason="smart_scheduled"),
        _cycle(120, current=16.0, price=0.12, reason="smart_scheduled"),
        _cycle(180, current=0.0, price=0.50, reason="smart_wait_cheaper"),
    ]
    result = compute_charging_savings(cycles, phases=3, nominal_voltage_v=230.0)
    assert result.charging_intervals == 2
    assert result.energy_kwh > 0
    assert result.actual_cost_sek < result.baseline_cost_sek
    assert result.savings_sek > 0
    assert result.savings_pct > 0
    assert result.savings_ore == round(result.savings_sek * 100)


def test_savings_excludes_override_interval():
    cycles = [
        _cycle(0, current=16.0, price=0.10, reason="smart_scheduled"),
        EvBridgeCycleRecord(
            charger_id=1,
            recorded_at=_cycle(60, current=16.0, price=0.10).recorded_at,
            applied_current_a=16.0,
            price_kwh=0.10,
            policy_mode="override",
            decision_reason="manual_override",
            override_active=True,
            vehicle_connected=True,
        ),
        _cycle(120, current=0.0, price=0.50, reason="smart_wait_cheaper"),
    ]
    result = compute_charging_savings(cycles, phases=3, nominal_voltage_v=230.0)
    assert result.charging_intervals == 1
