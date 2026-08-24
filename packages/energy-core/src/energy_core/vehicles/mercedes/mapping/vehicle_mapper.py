"""Map Mercedes attributes to normalized VehicleState."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.constants import (
    ATTRIBUTE_CHARGING_ACTIVE,
    ATTRIBUTE_CHARGING_POWER_KW,
    ATTRIBUTE_CHARGING_STATUS,
    ATTRIBUTE_MAX_SOC,
    ATTRIBUTE_RANGE_ELECTRIC_KM,
    ATTRIBUTE_SOC,
    STALE_TELEMETRY_SECONDS,
)
from energy_core.vehicles.mercedes.commands.features import MercedesCommandFeatures
from energy_core.vehicles.vin import mask_vin

logger = logging.getLogger(__name__)


class MercedesCapabilityMapper:
    @staticmethod
    def from_rest_payload(
        payload: dict[str, Any],
        *,
        command_payload: dict[str, Any] | list[Any] | None = None,
    ) -> VehicleCapabilities:
        features = {str(item).lower() for item in payload.get("features", []) if item}
        commands = {str(item).lower() for item in payload.get("commands", []) if item}
        command_features = MercedesCommandFeatures.from_rest_payload(command_payload or {})
        can_set_target_soc = (
            command_features.supports_set_target_soc()
            or "battery_max_soc" in features
            or "max_soc" in features
            or "battery_max_soc_configure" in commands
            or "charging_configure" in commands
            or "charge_program_configure" in commands
        )
        can_start_charging = command_features.supports_start_charging() or "start" in commands
        can_stop_charging = command_features.supports_stop_charging() or "stop" in commands
        return VehicleCapabilities(
            can_read_soc=True,
            can_read_range=True,
            can_read_charging_state=True,
            can_read_charging_power="chargingpower" in features or "charging" in features,
            can_read_target_soc="battery_max_soc" in features or "max_soc" in features,
            can_read_departure_time="departuretime" in features,
            can_set_target_soc=can_set_target_soc,
            can_start_charging=can_start_charging,
            can_stop_charging=can_stop_charging,
        )


class MercedesVehicleMapper:
    def __init__(self) -> None:
        self._attributes: dict[str, dict[str, Any]] = {}

    def apply_discovery(
        self,
        *,
        vehicle_id: str,
        vin: str | None,
        manufacturer: str,
        model: str,
        capabilities: VehicleCapabilities,
    ) -> VehicleState:
        now = datetime.now(UTC)
        return VehicleState(
            vehicle_id=vehicle_id,
            provider="mercedes",
            manufacturer=manufacturer,
            model=model,
            vin=vin,
            capabilities=capabilities,
            connection_state=VehicleConnectionState.CONNECTED,
            last_provider_update=now,
            data_quality=DataQuality.UNKNOWN,
        )

    def apply_push(self, base: VehicleState, message: MercedesPushMessage) -> VehicleState:
        bucket = self._attributes.setdefault(base.vehicle_id, {})
        for attr in message.attributes:
            bucket[attr.name.lower()] = attr.value
        now = datetime.now(UTC)
        soc = _to_float(bucket.get(ATTRIBUTE_SOC))
        target_soc = _to_float(bucket.get(ATTRIBUTE_MAX_SOC))
        range_km = _to_float(bucket.get(ATTRIBUTE_RANGE_ELECTRIC_KM.lower()))
        power_kw = _to_float(bucket.get(ATTRIBUTE_CHARGING_POWER_KW.lower()))
        charging_status = str(bucket.get(ATTRIBUTE_CHARGING_STATUS, "") or "").lower()
        charging_active = _to_bool(bucket.get(ATTRIBUTE_CHARGING_ACTIVE))
        is_charging = charging_active
        if charging_status:
            is_charging = charging_status in {"charging", "active", "quickcharging", "accharging", "dccharging"}
        is_plugged_in = None
        if charging_status:
            is_plugged_in = charging_status not in {"unplugged", "none", "invalid"}
        quality = DataQuality.MEASURED if soc is not None else DataQuality.UNKNOWN
        return VehicleState(
            vehicle_id=base.vehicle_id,
            provider=base.provider,
            manufacturer=base.manufacturer,
            model=base.model,
            vin=message.vin or base.vin,
            state_of_charge_percent=soc,
            target_soc_percent=target_soc,
            electric_range_km=range_km,
            is_plugged_in=is_plugged_in,
            is_charging=is_charging,
            charging_power_kw=power_kw,
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=quality,
            last_vehicle_update=now,
            last_provider_update=now,
            soc_quality=DataQuality.MEASURED if soc is not None else DataQuality.UNKNOWN,
            charging_power_quality=DataQuality.MEASURED if power_kw is not None else DataQuality.UNKNOWN,
            range_quality=DataQuality.MEASURED if range_km is not None else DataQuality.UNKNOWN,
            capabilities=base.capabilities,
        )

    def mark_stale(self, state: VehicleState) -> VehicleState:
        if state.last_vehicle_update is None:
            return state
        age = (datetime.now(UTC) - state.last_vehicle_update).total_seconds()
        if age <= STALE_TELEMETRY_SECONDS:
            return state
        return replace(
            state,
            data_quality=DataQuality.STALE,
            connection_state=VehicleConnectionState.DEGRADED,
        )


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off"}:
        return False
    return None
