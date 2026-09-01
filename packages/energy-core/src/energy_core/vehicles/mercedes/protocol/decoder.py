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
    ATTRIBUTE_POSITION_LAT,
    ATTRIBUTE_POSITION_LONG,
    ATTRIBUTE_RANGE_ELECTRIC_KM,
    ATTRIBUTE_SOC,
)
from energy_core.vehicles.mercedes.protocol.proto import vehicle_events_pb2

logger = logging.getLogger(__name__)

_PREFER_DISPLAY_VALUE = frozenset({ATTRIBUTE_CHARGING_STATUS, ATTRIBUTE_CHARGING_ACTIVE})

_REST_STATUS_FIELD_ALIASES = {
    "soc": ATTRIBUTE_SOC,
    "max_soc": ATTRIBUTE_MAX_SOC,
    "position_lat": ATTRIBUTE_POSITION_LAT,
    "position_long": ATTRIBUTE_POSITION_LONG,
    "position_heading": "positionheading",
    "rangeelectric": ATTRIBUTE_RANGE_ELECTRIC_KM.lower(),
    "range_electric_wltp": ATTRIBUTE_RANGE_ELECTRIC_KM.lower(),
    "overall_range": ATTRIBUTE_RANGE_ELECTRIC_KM.lower(),
    "charging_power": ATTRIBUTE_CHARGING_POWER_KW.lower(),
    "chargingactive": ATTRIBUTE_CHARGING_ACTIVE,
    "chargingstatus": ATTRIBUTE_CHARGING_STATUS,
}

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
        """Decode widget REST ``vehicleattributes`` payloads."""
        try:
            legacy = vehicle_events_pb2.VehicleStatus()
            legacy.ParseFromString(payload)
            if legacy.attributes:
                return self._map_vep_update(legacy)
        except (DecodeError, TypeError):
            pass
        try:
            update = vehicle_events_pb2.VehicleStatusUpdate()
            update.ParseFromString(payload)
        except (DecodeError, TypeError):
            return None
        if not update.ListFields():
            return None
        return self._map_vehicle_status_update(update)

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
            name = _normalize_attribute_name(str(key))
            value = _extract_attribute_status_value(status, attribute_key=name)
            if value is None:
                continue
            attributes.append(MercedesAttributeUpdate(name=name, value=value, vin=vin))
        if not attributes:
            return MercedesPushMessage(attributes=(), vin=vin)
        return MercedesPushMessage(attributes=tuple(attributes), vin=vin)

    def _map_vehicle_status_update(self, update: Any) -> MercedesPushMessage | None:
        vin = str(update.fin_or_vin) if getattr(update, "fin_or_vin", None) else None
        attributes: list[MercedesAttributeUpdate] = []
        for field_desc, field_obj in update.ListFields():
            if field_desc.name == "fin_or_vin":
                continue
            alias = _REST_STATUS_FIELD_ALIASES.get(field_desc.name)
            if alias is None:
                continue
            value = _extract_status_update_value(field_obj, attribute_key=alias)
            if value is None:
                continue
            normalized = _normalize_power_value(alias, value)
            attributes.append(MercedesAttributeUpdate(name=alias, value=normalized, vin=vin))
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
        "positionlat": "positionlat",
        "positionlong": "positionlong",
        "positionheading": "positionheading",
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


def _extract_attribute_status_value(status: Any, *, attribute_key: str | None = None) -> Any:
    display_value = getattr(status, "display_value", None)
    if attribute_key in _PREFER_DISPLAY_VALUE and display_value not in (None, ""):
        return display_value
    for field_name in ("double_value", "int_value", "bool_value", "string_value"):
        if status.HasField(field_name):
            value = getattr(status, field_name)
            if value not in (None, ""):
                return value
    if display_value not in (None, ""):
        return display_value
    return None


def _metadata_unavailable(status_obj: Any) -> bool:
    metadata = getattr(status_obj, "metadata", None)
    if metadata is None:
        return False
    status = getattr(metadata, "status", None)
    if status is None:
        return False
    text = str(status)
    return "NOT_AVAILABLE" in text or text.endswith("VALUE_NOT_AVAILABLE")


def _extract_status_update_value(status_obj: Any, *, attribute_key: str | None = None) -> Any:
    if _metadata_unavailable(status_obj):
        return None
    display_value = getattr(status_obj, "display_value", None)
    if attribute_key in _PREFER_DISPLAY_VALUE and display_value not in (None, ""):
        return display_value
    value = getattr(status_obj, "value", None)
    if value not in (None, ""):
        if isinstance(value, (int, float, bool)):
            return value
        text = str(value)
        if text and not text.isupper():
            return text
        if display_value not in (None, ""):
            return display_value
        return text
    if display_value not in (None, ""):
        return display_value
    return None
