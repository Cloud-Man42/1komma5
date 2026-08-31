"""Charging type classification."""

from __future__ import annotations

from enum import StrEnum


class ChargingType(StrEnum):
    AC = "AC"
    DC = "DC"
    HPC = "HPC"
    UNKNOWN = "UNKNOWN"


def classify_charging_type(
    *,
    charger_type_hint: str | None = None,
    charging_power_kw: float | None = None,
    location_expected_type: str | None = None,
) -> ChargingType:
    if location_expected_type:
        normalized = location_expected_type.upper()
        if normalized in {"AC", "DC", "HPC"}:
            return ChargingType(normalized)
    if charger_type_hint:
        hint = charger_type_hint.lower()
        if "halo" in hint or "charge amps" in hint or "ac" in hint:
            return ChargingType.AC
    if charging_power_kw is not None:
        if charging_power_kw >= 100:
            return ChargingType.HPC
        if charging_power_kw >= 40:
            return ChargingType.DC
        if charging_power_kw > 0:
            return ChargingType.AC
    return ChargingType.UNKNOWN
