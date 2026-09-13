"""Match Heartbeat discovery payloads by serial number."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_SERIAL_KEYS = ("serialNumber", "serial_number", "serial", "gridxHardwareId", "hardwareId")


@dataclass(frozen=True, slots=True)
class SerialMatchResult:
    serial: str
    found: bool
    matches: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    resolved_site_id: str | None = None
    resolved_system_id: str | None = None
    resolved_asset_id: str | None = None
    resolved_device_id: str | None = None


def normalize_serial(value: str) -> str:
    return re.sub(r"[\s\-_]+", "", value.strip().upper())


def find_serial_in_tree(data: Any, target_serial: str) -> list[dict[str, Any]]:
    normalized_target = normalize_serial(target_serial)
    matches: list[dict[str, Any]] = []

    def walk(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_str = str(key)
                if key_str in _SERIAL_KEYS and isinstance(value, str):
                    if normalize_serial(value) == normalized_target:
                        matches.append({"path": ".".join(path + (key_str,)), "node": node})
                walk(value, path + (key_str,))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, path + (str(index),))

    walk(data, ())
    return matches


def resolve_ids_from_match(match_node: dict[str, Any]) -> dict[str, str | None]:
    node = match_node.get("node") if isinstance(match_node.get("node"), dict) else match_node
    if not isinstance(node, dict):
        return {
            "heartbeat_site_id": None,
            "heartbeat_system_id": None,
            "heartbeat_asset_id": None,
            "heartbeat_device_id": None,
        }
    return {
        "heartbeat_site_id": _first_str(node, "siteId", "site_id"),
        "heartbeat_system_id": _first_str(node, "systemId", "system_id", "id"),
        "heartbeat_asset_id": _first_str(node, "assetId", "asset_id"),
        "heartbeat_device_id": _first_str(node, "deviceId", "device_id", "gridxHardwareId"),
    }


def _first_str(node: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = node.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def match_serial(data: Any, target_serial: str) -> SerialMatchResult:
    matches = find_serial_in_tree(data, target_serial)
    if not matches:
        return SerialMatchResult(serial=target_serial, found=False)
    resolved = resolve_ids_from_match(matches[0])
    return SerialMatchResult(
        serial=target_serial,
        found=True,
        matches=tuple(matches),
        resolved_site_id=resolved["heartbeat_site_id"],
        resolved_system_id=resolved["heartbeat_system_id"],
        resolved_asset_id=resolved["heartbeat_asset_id"],
        resolved_device_id=resolved["heartbeat_device_id"],
    )
