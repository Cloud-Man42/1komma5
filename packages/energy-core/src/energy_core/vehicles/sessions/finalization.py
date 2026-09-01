"""Finalize and repair vehicle charge session metadata."""

from __future__ import annotations

from typing import Any

from energy_core.db.models import VehicleStateLatestModel
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRecord
from energy_core.integrations.charging_stations.models import ResolvedChargingLocation, StationResolutionStatus
from energy_core.vehicles.charging_intelligence.location import AWAY_LOCATION_NAME
from energy_core.vehicles.sessions.constants import estimate_battery_delta_kwh

_UNKNOWN_LOCATION_NAMES = frozenset({"Unknown", AWAY_LOCATION_NAME})


def is_unknown_location(name: str | None) -> bool:
    if not name:
        return True
    return name.strip() in _UNKNOWN_LOCATION_NAMES


def finalize_away_session_energy(
    active: VehicleChargeSessionRecord,
    *,
    end_soc: float | None,
    context_estimated_kwh: float | None,
    usable_battery_kwh: float | None = None,
) -> tuple[float | None, float | None, str]:
    """Return halo_energy_kwh, estimated_battery_energy_delta_kwh, energy_quality."""
    delta = estimate_battery_delta_kwh(
        active.start_soc,
        end_soc,
        usable_battery_kwh=usable_battery_kwh,
    )
    energy = delta if delta is not None and delta > 0 else context_estimated_kwh
    if energy is not None and energy > 0:
        return energy, delta, "ESTIMATED"
    return None, delta, "UNKNOWN"


def merge_csi_fields(
    existing: VehicleChargeSessionRecord | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    """Keep the best-known station/location when new telemetry would downgrade it."""
    if existing is None:
        return incoming

    merged = dict(incoming)
    if is_unknown_location(merged.get("location_name")) and not is_unknown_location(existing.location_name):
        merged["location_name"] = existing.location_name
    if not merged.get("station_name") and existing.station_name:
        merged["station_name"] = existing.station_name
    if not merged.get("charger_operator") and existing.charger_operator:
        merged["charger_operator"] = existing.charger_operator
    if not merged.get("station_provider") and existing.station_provider:
        merged["station_provider"] = existing.station_provider
    if not merged.get("station_provider_id") and existing.station_provider_id:
        merged["station_provider_id"] = existing.station_provider_id
    if merged.get("station_confidence") in {None, 0} and existing.station_confidence:
        merged["station_confidence"] = existing.station_confidence
    if is_unknown_location(merged.get("location_name")) and existing.latitude and existing.longitude:
        merged["latitude"] = existing.latitude
        merged["longitude"] = existing.longitude
    return merged


def apply_station_resolution_to_csi(
    csi_fields: dict[str, Any],
    station_resolution: ResolvedChargingLocation | None,
    *,
    latest: VehicleStateLatestModel | None,
) -> dict[str, Any]:
    if station_resolution is None:
        return csi_fields
    if (
        not is_unknown_location(csi_fields.get("location_name"))
        and station_resolution.station_resolution_status == StationResolutionStatus.UNKNOWN
    ):
        return csi_fields

    updated = dict(csi_fields)
    if station_resolution.location_name:
        updated["location_name"] = station_resolution.location_name
    if station_resolution.station_name:
        updated["station_name"] = station_resolution.station_name
    if station_resolution.operator_name:
        updated["charger_operator"] = station_resolution.operator_name
    if station_resolution.charging_type:
        updated["charging_type"] = station_resolution.charging_type
    if station_resolution.connector_type:
        updated["connector_type"] = station_resolution.connector_type
    if station_resolution.confidence is not None:
        updated["station_confidence"] = station_resolution.confidence
    if station_resolution.station_resolution_status:
        updated["station_resolution_status"] = station_resolution.station_resolution_status.value
    if station_resolution.identification_method:
        updated["identification_method"] = station_resolution.identification_method
    if station_resolution.confidence_band:
        updated["detection_confidence"] = station_resolution.confidence_band
    if station_resolution.selected_station is not None:
        updated["station_provider"] = station_resolution.selected_station.provider.value
        updated["station_provider_id"] = station_resolution.selected_station.provider_station_id
    if latest is not None:
        if latest.latitude is not None:
            updated["latitude"] = latest.latitude
        if latest.longitude is not None:
            updated["longitude"] = latest.longitude
    return updated


def repair_completed_session_fields(
    record: VehicleChargeSessionRecord,
    *,
    station_resolution: ResolvedChargingLocation | None,
    usable_battery_kwh: float | None = None,
) -> dict[str, Any] | None:
    """Build patch fields for a completed session missing station or energy."""
    fields: dict[str, Any] = {}
    csi = {
        "location_name": record.location_name,
        "station_name": record.station_name,
        "charger_operator": record.charger_operator,
        "charging_type": record.charging_type,
        "connector_type": record.connector_type,
        "station_confidence": record.station_confidence,
        "station_resolution_status": record.station_resolution_status,
        "identification_method": record.identification_method,
        "detection_confidence": record.detection_confidence,
        "station_provider": record.station_provider,
        "station_provider_id": record.station_provider_id,
        "latitude": record.latitude,
        "longitude": record.longitude,
    }
    if station_resolution is not None and is_unknown_location(record.location_name):
        csi = apply_station_resolution_to_csi(csi, station_resolution, latest=None)
        for key, value in csi.items():
            if value is not None and getattr(record, key, None) != value:
                fields[key] = value

    energy, delta, quality = finalize_away_session_energy(
        record,
        end_soc=record.end_soc,
        context_estimated_kwh=record.estimated_energy_kwh,
        usable_battery_kwh=usable_battery_kwh,
    )
    current_energy = record.halo_energy_kwh or 0
    if energy is not None and energy > 0 and current_energy <= 0:
        fields["halo_energy_kwh"] = energy
        fields["estimated_battery_energy_delta_kwh"] = delta
        fields["energy_quality"] = quality
        fields["energy_source"] = "SOC_ESTIMATE"

    return fields or None
