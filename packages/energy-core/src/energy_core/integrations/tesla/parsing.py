"""Parse Tesla Fleet API vehicle payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.vehicles.abstractions.models import (
    DataQuality,
    VehicleCapabilities,
    VehicleConnectionState,
    VehicleState,
)


def _vehicle_capabilities() -> VehicleCapabilities:
    return VehicleCapabilities(
        can_read_soc=True,
        can_read_range=True,
        can_read_charging_state=True,
        can_read_charging_power=True,
        can_read_target_soc=True,
    )


def parse_vehicle_state(payload: dict[str, Any], *, now: datetime | None = None) -> VehicleState:
    now = now or datetime.now(UTC)
    charge_state = payload.get("charge_state") or {}
    drive_state = payload.get("drive_state") or {}
    vehicle_state = payload.get("vehicle_state") or {}
    vehicle_id = str(payload.get("id") or payload.get("id_s") or "tesla-vehicle")
    charging = bool(charge_state.get("charging_state") in {"Charging", "Starting"})
    connected = vehicle_state.get("api_version") is not None or payload.get("state") != "offline"
    soc = charge_state.get("battery_level")
    return VehicleState(
        vehicle_id=vehicle_id,
        provider="tesla",
        manufacturer="Tesla",
        model=str(payload.get("model") or vehicle_state.get("car_type") or "Model 3"),
        vin=str(payload.get("vin") or ""),
        state_of_charge_percent=float(soc) if soc is not None else None,
        electric_range_km=_to_float(drive_state.get("range")),
        charging_power_kw=_to_float(charge_state.get("charger_power")),
        is_charging=charging,
        connection_state=VehicleConnectionState.CONNECTED if connected else VehicleConnectionState.DISCONNECTED,
        data_quality=DataQuality.MEASURED if connected else DataQuality.STALE,
        capabilities=_vehicle_capabilities(),
        last_provider_update=now,
    )


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
