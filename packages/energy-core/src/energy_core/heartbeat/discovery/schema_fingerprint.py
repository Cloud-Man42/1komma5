"""Schema fingerprinting and unknown field detection for Heartbeat API responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any

KNOWN_EV_KEYS = frozenset(
    {
        "id",
        "profile",
        "chargeSettings",
        "manualSoc",
        "assignedChargerId",
        "name",
        "manufacturer",
        "model",
        "targetSoc",
        "chargingMode",
        "primaryScheduleDepartureTime",
        "batteryCapacity",
    }
)

KNOWN_WALLBOX_KEYS = frozenset(
    {
        "id",
        "gridxHardwareId",
        "assignedEvId",
        "name",
        "manufacturer",
        "model",
        "status",
        "serialNumber",
    }
)


def collect_json_paths(data: Any, *, prefix: str = "") -> set[str]:
    paths: set[str] = set()
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            paths.add(path)
            paths.update(collect_json_paths(value, prefix=path))
    elif isinstance(data, list) and data:
        paths.update(collect_json_paths(data[0], prefix=f"{prefix}[0]"))
    return paths


def unknown_fields(data: Any, known_keys: frozenset[str], *, prefix: str = "") -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            top_key = path.split(".")[0].split("[")[0]
            if prefix == "" and top_key not in known_keys:
                found.append(path)
            found.extend(unknown_fields(value, known_keys, prefix=path))
    elif isinstance(data, list):
        for index, item in enumerate(data[:3]):
            found.extend(unknown_fields(item, known_keys, prefix=f"{prefix}[{index}]"))
    return tuple(dict.fromkeys(found))


def schema_fingerprint(data: Any) -> str:
    paths = sorted(collect_json_paths(data))
    payload = json.dumps(paths, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
