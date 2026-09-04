"""EOV domain types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from energy_core.price_engine.types import StrategyState


class EnergyAction(StrEnum):
    USE_NOW = "USE_NOW"
    STORE_IN_BATTERY = "STORE_IN_BATTERY"
    EXPORT_TO_GRID = "EXPORT_TO_GRID"
    DISCHARGE_BATTERY = "DISCHARGE_BATTERY"
    WAIT = "WAIT"


@dataclass(frozen=True, slots=True)
class EovConfig:
    round_trip_efficiency: float = 0.92
    degradation_cost_sek_kwh: float = 0.02
    battery_capacity_kwh: float = 10.0
    lookahead_hours: int = 24
    shiftable_kwh_per_day: float = 10.0


@dataclass(frozen=True, slots=True)
class EovDecision:
    action: EnergyAction
    strategy_state: StrategyState
    expected_value_sek_kwh: float
    confidence: float
    reason: str
    reason_sv: str
    recommended_reserve_soc_pct: float | None
