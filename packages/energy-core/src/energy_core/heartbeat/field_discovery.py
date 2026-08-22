"""Safe discovery of EV/EMS-related fields in HeartBeat API responses."""

from __future__ import annotations

import re
from typing import Any

DISCOVERY_KEY_PATTERN = re.compile(
    r"(powerTarget|targetPower|chargingPower|evPower|plannedPower|setpoint|"
    r"powerSetpoint|schedule|chargingSchedule|optimization|optimizedPower|"
    r"flexibility|smartCharge|SMART_CHARGE|SOLAR_CHARGE|QUICK_CHARGE|targetSoc|"
    r"manualSoc|departure|marketPrice|activeChargingMode|evChargers)",
    re.IGNORECASE,
)

SENSITIVE_KEY_PATTERN = re.compile(
    r"(token|password|secret|email|serial|gridxStartCode|contactEmail|authorization)",
    re.IGNORECASE,
)


def discover_relevant_fields(data: Any, *, prefix: str = "") -> tuple[str, ...]:
    hints: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if SENSITIVE_KEY_PATTERN.search(str(key)):
                    continue
                if DISCOVERY_KEY_PATTERN.search(str(key)):
                    hints.append(_format_hint(child_path, child))
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value[:5]):
                walk(child, f"{path}[{index}]")

    walk(data, prefix)
    return tuple(dict.fromkeys(hints))


def _format_hint(path: str, value: Any) -> str:
    if isinstance(value, bool):
        return f"{path}=bool:{value}"
    if isinstance(value, (int, float)):
        return f"{path}=number:{value}"
    if isinstance(value, str) and len(value) <= 64:
        return f"{path}=str:{value}"
    if value is None:
        return f"{path}=null"
    return f"{path}=object"
