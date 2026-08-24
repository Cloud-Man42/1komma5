"""Correlate Mercedes vehicle telemetry with Charge Amps Halo readings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from energy_core.vehicles.abstractions.models import DataQuality, VehicleState

POWER_TOLERANCE_KW = 1.5
POWER_PARTIAL_TOLERANCE_KW = 3.0


class CorrelationStatus(StrEnum):
    ALIGNED = "ALIGNED"
    PARTIAL = "PARTIAL"
    MISMATCH = "MISMATCH"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class HaloChargerSnapshot:
    charger_id: int
    vehicle_connected: bool | None
    is_charging: bool | None
    power_kw: float | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class VehicleHaloCorrelationResult:
    charger_id: int | None
    confidence: float
    status: CorrelationStatus
    plugged_agreement: bool | None
    charging_agreement: bool | None
    power_delta_kw: float | None
    vehicle_power_kw: float | None
    halo_power_kw: float | None
    notes: str


def correlate_vehicle_with_halo(
    vehicle_state: VehicleState,
    halo: HaloChargerSnapshot | None,
) -> VehicleHaloCorrelationResult:
    if halo is None:
        return VehicleHaloCorrelationResult(
            charger_id=None,
            confidence=0.0,
            status=CorrelationStatus.UNAVAILABLE,
            plugged_agreement=None,
            charging_agreement=None,
            power_delta_kw=None,
            vehicle_power_kw=vehicle_state.charging_power_kw,
            halo_power_kw=None,
            notes="Ingen Halo-laddare kopplad",
        )

    if vehicle_state.data_quality == DataQuality.STALE:
        return _unavailable(
            halo.charger_id,
            vehicle_state.charging_power_kw,
            halo.power_kw,
            "Fordonsdata är inaktuell",
        )

    vehicle_plugged = vehicle_state.is_plugged_in
    vehicle_charging = vehicle_state.is_charging
    vehicle_power = vehicle_state.charging_power_kw
    halo_plugged = halo.vehicle_connected
    halo_charging = halo.is_charging
    halo_power = halo.power_kw

    if vehicle_plugged is None and vehicle_charging is None and vehicle_power is None:
        return _unavailable(halo.charger_id, vehicle_power, halo_power, "Mercedes saknar laddningssignal")

    if halo_plugged is None and halo_charging is None and halo_power is None:
        return _unavailable(halo.charger_id, vehicle_power, halo_power, "Halo saknar mätvärden")

    score = 0.0
    weight = 0.0
    plugged_agreement = _bool_agreement(vehicle_plugged, halo_plugged)
    if plugged_agreement is not None:
        score += 0.35 if plugged_agreement else 0.0
        weight += 0.35

    charging_agreement = _bool_agreement(vehicle_charging, halo_charging)
    if charging_agreement is not None:
        score += 0.35 if charging_agreement else 0.0
        weight += 0.35

    power_delta = None
    if vehicle_power is not None and halo_power is not None:
        power_delta = abs(vehicle_power - halo_power)
        weight += 0.30
        if power_delta <= POWER_TOLERANCE_KW:
            score += 0.30
        elif power_delta <= POWER_PARTIAL_TOLERANCE_KW:
            score += 0.15

    confidence = round(score / weight, 3) if weight > 0 else 0.0
    status = _status_from_confidence(confidence, weight)
    notes = _build_notes(plugged_agreement, charging_agreement, power_delta)

    return VehicleHaloCorrelationResult(
        charger_id=halo.charger_id,
        confidence=confidence,
        status=status,
        plugged_agreement=plugged_agreement,
        charging_agreement=charging_agreement,
        power_delta_kw=power_delta,
        vehicle_power_kw=vehicle_power,
        halo_power_kw=halo_power,
        notes=notes,
    )


def halo_snapshot_from_charger(charger) -> HaloChargerSnapshot:
    power_kw = None
    if charger.last_actual_power_w is not None:
        power_kw = round(charger.last_actual_power_w / 1000.0, 2)
    is_charging = None
    if power_kw is not None:
        is_charging = power_kw >= 0.3
    elif charger.last_actual_charging_current_a is not None:
        is_charging = charger.last_actual_charging_current_a > 0.5
    updated_at = charger.last_bridge_run_at or charger.last_heartbeat_data_at
    return HaloChargerSnapshot(
        charger_id=charger.id,
        vehicle_connected=charger.last_vehicle_connected,
        is_charging=is_charging,
        power_kw=power_kw,
        updated_at=updated_at,
    )


def _bool_agreement(left: bool | None, right: bool | None) -> bool | None:
    if left is None or right is None:
        return None
    return left == right


def _status_from_confidence(confidence: float, weight: float) -> CorrelationStatus:
    if weight <= 0:
        return CorrelationStatus.UNAVAILABLE
    if confidence >= 0.75:
        return CorrelationStatus.ALIGNED
    if confidence >= 0.4:
        return CorrelationStatus.PARTIAL
    return CorrelationStatus.MISMATCH


def _build_notes(
    plugged: bool | None,
    charging: bool | None,
    power_delta: float | None,
) -> str:
    parts: list[str] = []
    if plugged is False:
        parts.append("Anslutningsstatus skiljer sig")
    if charging is False:
        parts.append("Laddstatus skiljer sig")
    if power_delta is not None and power_delta > POWER_TOLERANCE_KW:
        parts.append(f"Effektavvikelse {power_delta:.1f} kW")
    if not parts:
        return "Mercedes och Halo rapporterar överensstämmande laddning"
    return "; ".join(parts)


def _unavailable(
    charger_id: int | None,
    vehicle_power: float | None,
    halo_power: float | None,
    note: str,
) -> VehicleHaloCorrelationResult:
    return VehicleHaloCorrelationResult(
        charger_id=charger_id,
        confidence=0.0,
        status=CorrelationStatus.UNAVAILABLE,
        plugged_agreement=None,
        charging_agreement=None,
        power_delta_kw=None,
        vehicle_power_kw=vehicle_power,
        halo_power_kw=halo_power,
        notes=note,
    )
