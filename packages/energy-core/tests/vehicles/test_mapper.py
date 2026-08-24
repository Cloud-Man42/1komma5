"""Mercedes mapper tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from dataclasses import replace

from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState
from energy_core.vehicles.mercedes.mapping.vehicle_mapper import MercedesCapabilityMapper, MercedesVehicleMapper
from energy_core.vehicles.mercedes.protocol.decoder import MercedesAttributeUpdate, MercedesPushMessage


def test_capability_mapper_reads_charging_features():
    caps = MercedesCapabilityMapper.from_rest_payload(
        {"features": ["chargingpower", "battery_max_soc"]},
        command_payload={"commands": ["CHARGING_CONFIGURE"]},
    )
    assert caps.can_read_charging_power is True
    assert caps.can_read_target_soc is True
    assert caps.can_set_target_soc is True
    assert caps.can_start_charging is True
    assert caps.can_stop_charging is True


def test_vehicle_mapper_applies_push_values():
    mapper = MercedesVehicleMapper()
    base = mapper.apply_discovery(
        vehicle_id="vin-1",
        vin="W1K12345678901234",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
        capabilities=VehicleCapabilities(can_read_soc=True),
    )
    updated = mapper.apply_push(
        base,
        MercedesPushMessage(
            vin="W1K12345678901234",
            attributes=(
                MercedesAttributeUpdate(name="soc", value=34),
                MercedesAttributeUpdate(name="max_soc", value=80),
                MercedesAttributeUpdate(name="chargingpowerkw", value=7.4),
                MercedesAttributeUpdate(name="rangeElectricKm", value=220),
                MercedesAttributeUpdate(name="chargingstatus", value="charging"),
            ),
        ),
    )
    assert updated.state_of_charge_percent == 34
    assert updated.target_soc_percent == 80
    assert updated.charging_power_kw == 7.4
    assert updated.is_charging is True
    assert updated.data_quality == DataQuality.MEASURED


def test_vehicle_mapper_marks_stale_data():
    mapper = MercedesVehicleMapper()
    now = datetime.now(UTC)
    state = mapper.apply_discovery(
        vehicle_id="vin-1",
        vin="W1K12345678901234",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
        capabilities=VehicleCapabilities(),
    )
    stale = mapper.mark_stale(
        replace(
            state,
            last_vehicle_update=now - timedelta(minutes=10),
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=DataQuality.MEASURED,
        )
    )
    assert stale.data_quality == DataQuality.STALE
