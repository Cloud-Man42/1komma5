"""Tests for energy state service helpers."""

from energy_core.energy_state.models import BatteryState
from energy_core.energy_state.service import _derive_battery_state, _map_ev_state


def test_battery_state_charging():
    assert _derive_battery_state(soc=74.0, power_w=2300.0) == BatteryState.CHARGING


def test_battery_state_discharging():
    assert _derive_battery_state(soc=74.0, power_w=-1500.0) == BatteryState.DISCHARGING


def test_battery_state_full():
    assert _derive_battery_state(soc=99.5, power_w=0.0) == BatteryState.FULL


def test_battery_state_idle_deadband():
    assert _derive_battery_state(soc=74.0, power_w=10.0) == BatteryState.IDLE


class _Bridge:
    smart_charging_state = "WAITING_TO_START"
    halo_connected = True
    vehicle_connected = True


def test_ev_state_waiting():
    state = _map_ev_state(
        charger_available=True,
        bridge_status=_Bridge(),
        connection_status="CONNECTED",
        power_w=0.0,
    )
    from energy_core.energy_state.models import EvState

    assert state == EvState.WAITING
