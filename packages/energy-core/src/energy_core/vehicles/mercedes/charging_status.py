"""Mercedes chargingstatus enum decoding (mbapi2020 reference)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ChargingStatusInterpretation:
    label: str
    is_plugged_in: bool | None
    is_charging: bool | None


# Internal enum values documented in mbapi2020 (v0.29+).
_STATUS_BY_CODE: dict[int, ChargingStatusInterpretation] = {
    0: ChargingStatusInterpretation("charging", True, True),
    1: ChargingStatusInterpretation("charging_ends", True, False),
    2: ChargingStatusInterpretation("charge_break", True, False),
    3: ChargingStatusInterpretation("unplugged", False, False),
    4: ChargingStatusInterpretation("failure", True, False),
    5: ChargingStatusInterpretation("slow", True, True),
    6: ChargingStatusInterpretation("fast", True, True),
    7: ChargingStatusInterpretation("discharging", True, False),
    8: ChargingStatusInterpretation("not_charging", None, False),
    9: ChargingStatusInterpretation("slow_after_trip_target", True, True),
    10: ChargingStatusInterpretation("charging_after_trip_target", True, True),
    11: ChargingStatusInterpretation("fast_after_trip_target", True, True),
    12: ChargingStatusInterpretation("communication_with_evse", True, False),
    13: ChargingStatusInterpretation("ac_charging", True, True),
    14: ChargingStatusInterpretation("dc_charging", True, True),
    15: ChargingStatusInterpretation("battery_calibration", True, False),
    16: ChargingStatusInterpretation("unknown", None, False),
}

_STRING_ALIASES: dict[str, ChargingStatusInterpretation] = {
    "charging": ChargingStatusInterpretation("charging", True, True),
    "active": ChargingStatusInterpretation("charging", True, True),
    "quickcharging": ChargingStatusInterpretation("fast", True, True),
    "accharging": ChargingStatusInterpretation("ac_charging", True, True),
    "dccharging": ChargingStatusInterpretation("dc_charging", True, True),
    "unplugged": ChargingStatusInterpretation("unplugged", False, False),
    "notplugged": ChargingStatusInterpretation("unplugged", False, False),
    "disconnected": ChargingStatusInterpretation("unplugged", False, False),
    "nocharging": ChargingStatusInterpretation("not_charging", None, False),
    "notcharging": ChargingStatusInterpretation("not_charging", None, False),
    "not_charging": ChargingStatusInterpretation("not_charging", None, False),
}


def interpret_charging_status(value: Any) -> ChargingStatusInterpretation | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return ChargingStatusInterpretation("chargingactive", None, value)
    if isinstance(value, int):
        return _STATUS_BY_CODE.get(value)
    if isinstance(value, float) and value.is_integer():
        return _STATUS_BY_CODE.get(int(value))

    text = str(value).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if text.isdigit():
        return _STATUS_BY_CODE.get(int(text))
    return _STRING_ALIASES.get(text)
