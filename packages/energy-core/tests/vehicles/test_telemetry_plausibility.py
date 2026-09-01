"""Tests for Mercedes sleeping/placeholder telemetry rejection."""

from __future__ import annotations

from dataclasses import replace

from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.telemetry_plausibility import has_plausible_vehicle_telemetry, sanitize_vehicle_state


def _state(**kwargs) -> VehicleState:
    base = VehicleState(
        vehicle_id="vin-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE",
        connection_state=VehicleConnectionState.CONNECTED,
        data_quality=DataQuality.UNKNOWN,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )
    return replace(base, **kwargs)


def test_sleeping_placeholder_soc_zero_and_range_zero_is_not_plausible():
    state = _state(state_of_charge_percent=0.0, electric_range_km=0.0)
    assert has_plausible_vehicle_telemetry(state) is False


def test_real_soc_is_plausible():
    state = _state(state_of_charge_percent=16.0, electric_range_km=0.0)
    assert has_plausible_vehicle_telemetry(state) is True


def test_sanitize_drops_placeholder_soc_and_range():
    state = _state(state_of_charge_percent=0.0, electric_range_km=0.0, is_plugged_in=True)
    cleaned = sanitize_vehicle_state(state)
    assert cleaned.state_of_charge_percent is None
    assert cleaned.electric_range_km is None
