"""Shared vehicle-connection heuristics for Charge Amps connectors."""

from __future__ import annotations

from typing import Any

_VEHICLE_CONNECTED_STATUSES = frozenset(
    {"Charging", "Preparing", "SuspendedEV", "Finishing", "SuspendedEVSE", "Occupied"}
)


def _normalized_status(value: Any) -> str:
    return str(value or "").strip()


def _status_indicates_vehicle_connected(status: str) -> bool:
    if not status:
        return False
    normalized = status.casefold()
    return any(known.casefold() == normalized for known in _VEHICLE_CONNECTED_STATUSES)


def _truthy(value: Any) -> bool:
    return value is True or value == 1 or str(value).lower() in {"true", "1", "yes", "on"}


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _connector_voltage_v(connector: dict[str, Any]) -> float | None:
    voltages = [_float_or_none(connector.get(f"voltage{i}")) for i in (1, 2, 3)]
    values = [value for value in voltages if value is not None and value > 0]
    if not values:
        return None
    return max(values)


def vehicle_connected_from_web_connector(connector: dict[str, Any]) -> bool:
    if _truthy(connector.get("isCharging")):
        return True
    ocpp = _normalized_status(connector.get("ocppStatus"))
    if _status_indicates_vehicle_connected(ocpp):
        return True
    ev_state = _normalized_status(connector.get("evConnectorState"))
    if ev_state.casefold() in {"connected", "plugged", "evconnected", "occupied", "cableconnected"}:
        return True
    voltage = _connector_voltage_v(connector)
    if voltage is not None and voltage >= 100:
        return True
    return False


def vehicle_connected_from_external_connector(connector: dict[str, Any]) -> bool:
    ocpp = _normalized_status(connector.get("status") or connector.get("ocppStatus"))
    if _truthy(connector.get("isCharging") or connector.get("is_charging")):
        return True
    for key in (
        "evConnected",
        "ev_connected",
        "vehicleConnected",
        "vehicle_connected",
        "cablePlugged",
        "cable_plugged",
    ):
        if _truthy(connector.get(key)):
            return True
    return _status_indicates_vehicle_connected(ocpp)
