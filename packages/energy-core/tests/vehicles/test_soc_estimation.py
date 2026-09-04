"""Tests for Mercedes SoC estimation helpers."""

from __future__ import annotations

from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.soc_estimation import (
    apply_range_based_soc_correction,
    derive_soc_from_range_change,
    parse_soc_percent,
    resolve_soc_value,
)


def test_parse_soc_percent_accepts_display_strings():
    assert parse_soc_percent("37 %") == 37.0
    assert parse_soc_percent("37,5%") == 37.5


def test_resolve_soc_value_prefers_display_when_diverged():
    assert resolve_soc_value(31, "37 %") == 37.0
    assert resolve_soc_value(31, "31 %") == 31.0


def test_derive_soc_from_range_change():
    estimated = derive_soc_from_range_change(prior_soc=31.0, prior_range_km=131.0, new_range_km=156.0)
    assert estimated == 36.9


def test_apply_range_based_soc_correction_updates_state():
    state = VehicleState(
        vehicle_id="vin-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE",
        state_of_charge_percent=31.0,
        electric_range_km=156.0,
        connection_state=VehicleConnectionState.CONNECTED,
        data_quality=DataQuality.MEASURED,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )
    corrected = apply_range_based_soc_correction(state, prior_soc=31.0, prior_range_km=131.0)
    assert corrected.state_of_charge_percent == 36.9
    assert corrected.data_quality == DataQuality.ESTIMATED


def test_apply_range_based_soc_correction_ignores_small_range_delta():
    state = VehicleState(
        vehicle_id="vin-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE",
        state_of_charge_percent=31.0,
        electric_range_km=132.0,
        connection_state=VehicleConnectionState.CONNECTED,
        data_quality=DataQuality.MEASURED,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )
    corrected = apply_range_based_soc_correction(state, prior_soc=31.0, prior_range_km=131.0)
    assert corrected.state_of_charge_percent == 31.0
    assert corrected.data_quality == DataQuality.MEASURED
