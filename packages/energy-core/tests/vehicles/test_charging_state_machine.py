"""Tests for vehicle charging state machine."""

from __future__ import annotations

from energy_core.vehicles.charging_intelligence.state_machine import ChargingState, VehicleChargingStateMachine


def test_plug_in_then_charge():
    sm = VehicleChargingStateMachine()
    sm.apply(is_plugged_in=True, is_charging=False, trigger="plug")
    assert sm.state == ChargingState.PLUGGED_IN
    sm.apply(is_plugged_in=True, is_charging=True, trigger="charge")
    assert sm.state == ChargingState.CHARGING


def test_unplug_after_charge():
    sm = VehicleChargingStateMachine(initial=ChargingState.CHARGING)
    transition = sm.apply(is_plugged_in=False, is_charging=False, trigger="unplug")
    assert transition is not None
    assert sm.state == ChargingState.DISCONNECTED_AFTER_CHARGE
