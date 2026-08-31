"""Vehicle charge session constants."""

from __future__ import annotations

CALCULATION_VERSION = "vehicle-charge-v1"
DEFAULT_SAVINGS_BASELINE = "IMMEDIATE_GRID_CHARGING"
DEFAULT_BATTERY_CAPACITY_KWH = 90.0
SOC_TO_KWH_FACTOR = DEFAULT_BATTERY_CAPACITY_KWH / 100.0


def soc_to_kwh_factor(usable_battery_kwh: float | None) -> float:
    capacity = usable_battery_kwh if usable_battery_kwh and usable_battery_kwh > 0 else DEFAULT_BATTERY_CAPACITY_KWH
    return capacity / 100.0


def estimate_battery_delta_kwh(
    start_soc: float | None,
    end_soc: float | None,
    *,
    usable_battery_kwh: float | None = None,
) -> float | None:
    if start_soc is None or end_soc is None:
        return None
    delta = end_soc - start_soc
    if delta <= 0:
        return None
    return delta * soc_to_kwh_factor(usable_battery_kwh)
