"""Charging session cost resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CostSource(StrEnum):
    HOME_ENERGY_MODEL = "HOME_ENERGY_MODEL"
    CONFIGURED_FREE_CHARGING = "CONFIGURED_FREE_CHARGING"
    CONFIGURED_PER_KWH = "CONFIGURED_PER_KWH"
    CONFIGURED_FIXED = "CONFIGURED_FIXED"
    OPERATOR = "OPERATOR"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SessionCostEstimate:
    cost_sek: float | None
    cost_source: CostSource


def resolve_session_cost(
    *,
    home_charging: bool | None,
    actual_cost_sek: float | None,
    price_model: str | None,
    price_value: float | None,
    energy_kwh: float | None,
) -> SessionCostEstimate:
    if home_charging and actual_cost_sek is not None:
        return SessionCostEstimate(actual_cost_sek, CostSource.HOME_ENERGY_MODEL)
    if price_model == "FREE":
        return SessionCostEstimate(0.0, CostSource.CONFIGURED_FREE_CHARGING)
    if price_model == "FIXED" and price_value is not None:
        return SessionCostEstimate(price_value, CostSource.CONFIGURED_FIXED)
    if price_model == "PER_KWH" and price_value is not None and energy_kwh is not None:
        return SessionCostEstimate(round(energy_kwh * price_value, 2), CostSource.CONFIGURED_PER_KWH)
    return SessionCostEstimate(None, CostSource.UNKNOWN)
