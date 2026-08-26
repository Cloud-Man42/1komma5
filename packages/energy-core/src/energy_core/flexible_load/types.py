"""Domain types for flexible load optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class LoadStrategy(StrEnum):
    SMART = "SMART"
    SOLAR_ONLY = "SOLAR_ONLY"
    CHEAPEST = "CHEAPEST"
    FIXED_SCHEDULE = "FIXED_SCHEDULE"


class EnergySource(StrEnum):
    SOLAR = "SOLAR"
    BATTERY = "BATTERY"
    GRID = "GRID"
    MIXED = "MIXED"


@dataclass(frozen=True, slots=True)
class FlexibleLoad:
    load_id: str
    name: str
    nominal_power_w: float
    minimum_runtime: timedelta
    maximum_runtime: timedelta
    earliest_start: datetime
    latest_finish: datetime
    deadline: datetime
    minimum_interval: timedelta | None = None
    maximum_interval: timedelta | None = None
    preferred_energy_source: EnergySource = EnergySource.SOLAR
    maximum_allowed_cost_sek_kwh: float | None = None
    priority: int = 50
    interruptible: bool = False
    safety_critical: bool = True
    fixed_start: datetime | None = None
    fixed_end: datetime | None = None
    daily_runtime_target: timedelta | None = None
    max_starts_per_day: int | None = None
    minimum_pause: timedelta | None = None
    fixed_cycles_per_day: int | None = None
    fixed_cycle_duration: timedelta | None = None
    minimum_cycle_separation: timedelta | None = None


@dataclass(frozen=True, slots=True)
class HorizonBlock:
    timestamp: datetime
    solar_forecast_w: float
    house_load_forecast_w: float
    higher_priority_loads_w: float
    available_surplus_w: float
    battery_soc_pct: float | None
    spot_price_eur_kwh: float | None
    all_in_price_eur_kwh: float | None
    export_value_sek_kwh: float
    price_estimated: bool = False
    forecast_confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class ScoredBlock:
    block: HorizonBlock
    score: float
    solar_surplus_score: float
    low_price_score: float
    battery_availability_score: float
    deadline_score: float
    grid_import_penalty: float
    battery_depletion_penalty: float
    export_opportunity_penalty: float
    expected_energy_source: EnergySource
    marginal_cost_sek_kwh: float
    load_feasible: bool


@dataclass(frozen=True, slots=True)
class PlanWindow:
    start: datetime
    end: datetime
    duration: timedelta
    expected_energy_kwh: float
    expected_cost_sek: float
    expected_energy_source: EnergySource
    average_score: float
    blocks: tuple[ScoredBlock, ...] = ()


@dataclass(frozen=True, slots=True)
class LoadPlan:
    load_id: str
    strategy: LoadStrategy
    windows: tuple[PlanWindow, ...]
    reason: str
    reason_sv: str
    explanation_sv: str
    fallback_from_solar_only: bool = False
    fixed_schedule_analysis: bool = False
    alternative_windows: tuple[PlanWindow, ...] = field(default_factory=tuple)
    scored_blocks: tuple[ScoredBlock, ...] = field(default_factory=tuple)
    baseline_cost_sek: float | None = None
    planned_cost_sek: float | None = None
    savings_sek: float | None = None
