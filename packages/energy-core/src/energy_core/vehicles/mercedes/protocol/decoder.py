"""Decode Mercedes websocket protobuf frames."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from google.protobuf.message import DecodeError

from energy_core.vehicles.mercedes.constants import (
    ATTRIBUTE_CHARGING_ACTIVE,
    ATTRIBUTE_CHARGING_POWER_KW,
    ATTRIBUTE_CHARGING_STATUS,
    ATTRIBUTE_MAX_SOC,
    ATTRIBUTE_RANGE_ELECTRIC_KM,
    ATTRIBUTE_SOC,
)
from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2

logger = logging.getLogger(__name__)

_STATUS_UPDATE_FIELDS = {
    "soc": ATTRIBUTE_SOC,
    "max_soc": ATTRIBUTE_MAX_SOC,
    "target_soc": ATTRIBUTE_MAX_SOC,
    "charging_power": ATTRIBUTE_CHARGING_POWER_KW,
    "rangeelectric": ATTRIBUTE_RANGE_ELECTRIC_KM,
    "range_electric_wltp": ATTRIBUTE_RANGE_ELECTRIC_KM,
    "chargingstatus": ATTRIBUTE_CHARGING_STATUS,
    "chargingactive": ATTRIBUTE_CHARGING_ACTIVE,
}


@dataclass(frozen=True, slots=True)
class MercedesAttributeUpdate:
    name: str
    value: Any
    vin: str | None = None


@dataclass(frozen=True, slots=True)
class MercedesPushMessage:
    attributes: tuple[MercedesAttributeUpdate, ...] = ()
    vin: str | None = None


class MercedesMessageDecoder:
    def __init__(self) -> None:
        self.decode_failures = 0
        self.messages_received = 0
        self._unknown_attributes: set[str] = set()

    def decode(self, payload: bytes) -> MercedesPushMessage | None:
        self.messages_received += 1
        try:
            message = vehicle_events_pb2.PushMessage()
            message.ParseFromString(payload)
        except (DecodeError, TypeError) as exc:
            self.decode_failures += 1
            logger.debug("Mercedes protobuf decode failed: %s", exc.__class__.__name__)
            return None
        return self._map_push_message(message)

    def decode_vep_update(self, payload: bytes) -> MercedesPushMessage | None:
        try:
            message = vehicle_events_pb2.VEPUpdate()
            message.ParseFromString(payload)
        except (DecodeError, TypeError):
            return None
        return self._map_vep_update(message)

    def decode_vehicle_status(self, payload: bytes) -> MercedesPushMessage | None:
        """Decode widget REST ``vehicleattributes`` payloads (``VehicleStatus``)."""
        try:
            message = vehicle_events_pb2.VehicleStatus()
            message.ParseFromString(payload)
        except (DecodeError, TypeError):
            return None
        return self._map_vep_update(message)

    def _map_push_message(self, message: Any) -> MercedesPushMessage | None:
        msg_type = message.WhichOneof("msg")
        if msg_type == "vepUpdate":
            return self._map_vep_update(message.vepUpdate)
        if msg_type == "vepUpdates":
            attributes: list[MercedesAttributeUpdate] = []
            vin: str | None = None
            for update in message.vepUpdates.updates:
                mapped = self._map_vep_update(update)
                if mapped is None:
                    continue
                if mapped.vin and vin is None:
                    vin = mapped.vin
                attributes.extend(mapped.attributes)
            if not attributes:
                return None
            return MercedesPushMessage(attributes=tuple(attributes), vin=vin)
        if msg_type == "vehicle_status_updates":
            return self._map_vehicle_status_updates(message.vehicle_status_updates)
        return None

    def _map_vep_update(self, update: Any) -> MercedesPushMessage | None:
        vin = str(update.vin) if getattr(update, "vin", None) else None
        attributes: list[MercedesAttributeUpdate] = []
        for key, status in (update.attributes or {}).items():
            value = _extract_attribute_status_value(status)
            if value is None:
                continue
            name = _normalize_attribute_name(str(key))
            attributes.append(MercedesAttributeUpdate(name=name, value=value, vin=vin))
        if not attributes:
            return MercedesPushMessage(attributes=(), vin=vin)
        return MercedesPushMessage(attributes=tuple(attributes), vin=vin)

    def _map_vehicle_status_updates(self, updates: Any) -> MercedesPushMessage | None:
        attributes: list[MercedesAttributeUpdate] = []
        vin: str | None = None
        for _key, status_update in updates.vehicle_status_updates.items():
            current_vin = str(status_update.fin_or_vin) if getattr(status_update, "fin_or_vin", None) else vin
            if current_vin:
                vin = current_vin
            for field_name, attribute_name in _STATUS_UPDATE_FIELDS.items():
                if not status_update.HasField(field_name):
                    continue
                field_obj = getattr(status_update, field_name)
                value = _extract_status_field_value(field_obj)
                if value is None:
                    continue
                normalized = _normalize_power_value(attribute_name, value)
                attributes.append(
                    MercedesAttributeUpdate(name=attribute_name, value=normalized, vin=current_vin)
                )
        if not attributes:
            return None
        return MercedesPushMessage(attributes=tuple(attributes), vin=vin)


def _normalize_attribute_name(name: str) -> str:
    lowered = name.lower()
    aliases = {
        "chargingpower": ATTRIBUTE_CHARGING_POWER_KW,
        "charging_power": ATTRIBUTE_CHARGING_POWER_KW,
        "rangeelectric": ATTRIBUTE_RANGE_ELECTRIC_KM,
        "range_electric_km": ATTRIBUTE_RANGE_ELECTRIC_KM,
    }
    return aliases.get(lowered, lowered)


def _normalize_power_value(attribute_name: str, value: Any) -> Any:
    if attribute_name != ATTRIBUTE_CHARGING_POWER_KW:
        return value
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return value
    if numeric > 100:
        return numeric / 1000.0
    return numeric


def _extract_status_field_value(field_obj: Any) -> Any:
    for attr_name in ("value", "display_value"):
        if hasattr(field_obj, attr_name):
            value = getattr(field_obj, attr_name)
            if value not in (None, ""):
                return value
    return None


def _extract_attribute_status_value(status: Any) -> Any:
    for field_name in ("double_value", "int_value", "bool_value", "string_value"):
        if status.HasField(field_name):
            value = getattr(status, field_name)
            if value not in (None, ""):
                return value
    display_value = getattr(status, "display_value", None)
    if display_value not in (None, ""):
        return display_value
    return None
