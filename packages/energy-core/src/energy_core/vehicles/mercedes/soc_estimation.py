"""Derive plausible SoC when Mercedes widget REST returns stale soc values."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from energy_core.vehicles.abstractions.models import DataQuality, VehicleState

_SOC_DISPLAY_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*%?\s*$")


def parse_soc_percent(value: Any) -> float | None:
    """Parse Mercedes soc from int, float, or display strings like ``37 %``."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if 0.0 <= numeric <= 100.0 else None
    match = _SOC_DISPLAY_RE.match(str(value))
    if not match:
        return None
    numeric = float(match.group(1).replace(",", "."))
    return numeric if 0.0 <= numeric <= 100.0 else None


def resolve_soc_value(*candidates: Any, min_divergence: float = 1.0) -> float | None:
    """Prefer a fresher display soc when it materially diverges from the int value."""
    parsed = [parse_soc_percent(candidate) for candidate in candidates if candidate not in (None, "")]
    parsed = [value for value in parsed if value is not None]
    if not parsed:
        return None
    if len(parsed) == 1:
        return parsed[0]
    primary, secondary = parsed[0], parsed[1]
    if abs(secondary - primary) >= min_divergence:
        return secondary
    return primary


def derive_soc_from_range_change(
    *,
    prior_soc: float,
    prior_range_km: float,
    new_range_km: float,
    min_range_delta_ratio: float = 0.015,
) -> float | None:
    """Estimate soc from range movement when Mercedes keeps reporting the same soc."""
    if prior_range_km <= 0 or new_range_km <= 0:
        return None
    ratio = new_range_km / prior_range_km
    if abs(ratio - 1.0) < min_range_delta_ratio:
        return None
    estimated = prior_soc * ratio
    return max(0.0, min(100.0, round(estimated, 1)))


def apply_range_based_soc_correction(
    state: VehicleState,
    *,
    prior_soc: float | None,
    prior_range_km: float | None,
) -> VehicleState:
    """When range moves but soc is unchanged, derive a better soc estimate."""
    if (
        state.state_of_charge_percent is None
        or prior_soc is None
        or prior_range_km is None
        or state.electric_range_km is None
    ):
        return state
    if state.state_of_charge_percent != prior_soc:
        return state
    estimated = derive_soc_from_range_change(
        prior_soc=prior_soc,
        prior_range_km=prior_range_km,
        new_range_km=state.electric_range_km,
    )
    if estimated is None or abs(estimated - prior_soc) < 1.0:
        return state
    return replace(
        state,
        state_of_charge_percent=estimated,
        data_quality=DataQuality.ESTIMATED,
        soc_quality=DataQuality.ESTIMATED,
    )
