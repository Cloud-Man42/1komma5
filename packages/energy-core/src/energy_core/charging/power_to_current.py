"""Convert requested power (W) to charging current (A)."""

from __future__ import annotations

import math


def power_to_current_a(
    power_w: float,
    *,
    phases: int = 3,
    nominal_voltage_v: float = 230.0,
    power_factor: float = 1.0,
    min_current_a: float = 6.0,
    max_current_a: float = 16.0,
    max_power_w: float | None = None,
) -> float:
    if power_w <= 0:
        return 0.0

    if max_power_w is not None:
        power_w = min(power_w, max_power_w)

    if phases >= 3:
        denominator = math.sqrt(3) * nominal_voltage_v * power_factor
    else:
        denominator = nominal_voltage_v * power_factor

    if denominator <= 0:
        return 0.0

    current = power_w / denominator
    if current < min_current_a:
        return 0.0
    return min(current, max_current_a)


def current_to_power_w(
    current_a: float,
    *,
    phases: int = 3,
    nominal_voltage_v: float = 230.0,
    power_factor: float = 1.0,
) -> float:
    if current_a <= 0:
        return 0.0
    if phases >= 3:
        return current_a * math.sqrt(3) * nominal_voltage_v * power_factor
    return current_a * nominal_voltage_v * power_factor
