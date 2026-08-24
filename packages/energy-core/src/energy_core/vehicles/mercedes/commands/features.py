"""Mercedes command capability flags from REST discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MercedesCommandFeatures:
    charging_configure: bool = False
    battery_max_soc_configure: bool = False
    charge_program_configure: bool = False
    charge_coupler_stop: bool = False

    @classmethod
    def from_rest_payload(cls, payload: dict[str, Any] | list[Any] | None) -> MercedesCommandFeatures:
        available = _available_command_names(payload)
        return cls(
            charging_configure="CHARGING_CONFIGURE" in available,
            battery_max_soc_configure="BATTERY_MAX_SOC_CONFIGURE" in available,
            charge_program_configure="CHARGE_PROGRAM_CONFIGURE" in available
            or "BATTERY_CHARGE_PROGRAM_CONFIGURE" in available,
            charge_coupler_stop="CHARGE_COUPLER_STOP" in available,
        )

    def supports_set_target_soc(self) -> bool:
        return self.charging_configure or self.battery_max_soc_configure or self.charge_program_configure

    def supports_stop_charging(self) -> bool:
        return self.charge_coupler_stop or self.charging_configure

    def supports_start_charging(self) -> bool:
        return self.charging_configure


def _available_command_names(payload: dict[str, Any] | list[Any] | None) -> set[str]:
    if payload is None:
        return set()
    if isinstance(payload, list):
        names: set[str] = set()
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("isAvailable") is True and item.get("commandName"):
                names.add(str(item["commandName"]).upper())
        return names
    commands = payload.get("commands")
    if isinstance(commands, list) and commands and isinstance(commands[0], dict):
        return _available_command_names(commands)
    names = set()
    for key in ("commands", "features"):
        values = payload.get(key)
        if isinstance(values, list):
            names.update(str(item).upper() for item in values if item)
    if isinstance(payload, dict) and payload.get("commandName"):
        if payload.get("isAvailable") is True:
            names.add(str(payload["commandName"]).upper())
    return names
