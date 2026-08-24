"""Mercedes REST client tests."""

from __future__ import annotations

from energy_core.vehicles.mercedes.transport.rest_client import MercedesRestClient


def test_extract_vehicle_list_from_assigned_vehicles():
    payload = {
        "assignedVehicles": [
            {"fin": "W1K123", "model": "EQE 350+", "brand": "Mercedes-Benz"},
        ]
    }
    items = MercedesRestClient._extract_vehicle_list(payload)
    assert len(items) == 1
    assert items[0]["fin"] == "W1K123"


def test_extract_vehicle_list_from_v2_shape():
    payload = {"vehicles": [{"vin": "W1K123", "modelName": "EQE"}]}
    items = MercedesRestClient._extract_vehicle_list(payload)
    assert len(items) == 1
    assert items[0]["vin"] == "W1K123"
