"""Tests for vehicle domain models."""

from datetime import UTC, datetime

from energy_core.vehicles.abstractions.models import DataQuality, VehicleConnectionState, VehicleState
from energy_core.vehicles.vin import mask_vin


def test_mask_vin_hides_middle():
    assert mask_vin("W1K12345678901234") == "W1K***1234"


def test_mask_vin_short_values():
    assert mask_vin("AB") == "****"
    assert mask_vin(None) == ""


def test_vehicle_state_defaults_to_unknown_quality():
    state = VehicleState(
        vehicle_id="veh-1",
        provider="mock",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
    )
    assert state.data_quality == DataQuality.UNKNOWN
    assert state.connection_state == VehicleConnectionState.DISCONNECTED
    assert state.state_of_charge_percent is None


def test_vehicle_state_accepts_optional_telemetry():
    now = datetime.now(UTC)
    state = VehicleState(
        vehicle_id="veh-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
        state_of_charge_percent=47.0,
        target_soc_percent=80.0,
        electric_range_km=301.0,
        is_plugged_in=True,
        is_charging=True,
        charging_power_kw=7.2,
        last_vehicle_update=now,
        last_provider_update=now,
        data_quality=DataQuality.MEASURED,
        soc_quality=DataQuality.MEASURED,
    )
    assert state.charging_power_kw == 7.2
    assert state.last_vehicle_update == now
