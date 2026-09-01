"""Tests for vehicle charge session finalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from energy_core.integrations.charging_stations.models import (
    ChargingStationCandidate,
    ResolvedChargingLocation,
    StationProvider,
    StationResolutionStatus,
)
from energy_core.vehicles.sessions.finalization import (
    finalize_away_session_energy,
    is_unknown_location,
    merge_csi_fields,
    repair_completed_session_fields,
)


@dataclass
class _Record:
    id: int = 1
    vehicle_id: int = 1
    status: str = "COMPLETED"
    start_soc: float | None = 16.0
    end_soc: float | None = 31.0
    halo_energy_kwh: float | None = 0.0
    estimated_battery_energy_delta_kwh: float | None = None
    estimated_energy_kwh: float | None = None
    location_name: str | None = "Unknown"
    station_name: str | None = None
    charger_operator: str | None = None
    charging_type: str | None = "AC"
    connector_type: str | None = None
    station_confidence: int | None = None
    station_resolution_status: str | None = "UNKNOWN"
    identification_method: str | None = "UNKNOWN"
    detection_confidence: str | None = "LOW"
    station_provider: str | None = None
    station_provider_id: str | None = None
    latitude: float | None = 57.264
    longitude: float | None = 16.448
    charging_station_id: int | None = None


def test_is_unknown_location():
    assert is_unknown_location("Unknown") is True
    assert is_unknown_location("Hotell Corallen") is False


def test_finalize_away_session_energy_from_soc_delta():
    energy, delta, quality = finalize_away_session_energy(
        _Record(),
        end_soc=31.0,
        context_estimated_kwh=None,
    )
    assert energy == pytest.approx(13.5)
    assert delta == pytest.approx(13.5)
    assert quality == "ESTIMATED"


def test_merge_csi_fields_keeps_known_station():
    existing = _Record(location_name="Hotell Corallen", station_name="Hotell Corallen", charger_operator="ChargeNode")
    merged = merge_csi_fields(
        existing,
        {"location_name": "Unknown", "station_name": None, "charger_operator": None},
    )
    assert merged["location_name"] == "Hotell Corallen"
    assert merged["station_name"] == "Hotell Corallen"
    assert merged["charger_operator"] == "ChargeNode"


def test_repair_completed_session_fields_applies_chargefinder_result():
    resolution = ResolvedChargingLocation(
        location_name="Hotell Corallen",
        station_name="Hotell Corallen",
        operator_name="ChargeNode",
        charging_type="AC",
        connector_type="Type 2",
        max_power_kw=11.0,
        distance_meters=42.0,
        confidence=88,
        confidence_band="HIGH",
        identification_method="CHARGEFINDER",
        source="CHARGEFINDER",
        station_resolution_status=StationResolutionStatus.OK,
        selected_station=ChargingStationCandidate(
            provider=StationProvider.CHARGEFINDER,
            provider_station_id="cf-1",
            operator="ChargeNode",
            station_name="Hotell Corallen",
            latitude=57.264,
            longitude=16.448,
            charging_type="AC",
            connector_type="Type 2",
            max_power_kw=11.0,
            distance_m=42.0,
        ),
    )
    patch = repair_completed_session_fields(_Record(), station_resolution=resolution)
    assert patch is not None
    assert patch["location_name"] == "Hotell Corallen"
    assert patch["station_name"] == "Hotell Corallen"
    assert patch["charger_operator"] == "ChargeNode"
    assert patch["halo_energy_kwh"] == pytest.approx(13.5)
