"""Domain types for Heartbeat audit snapshots and rollups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AuditPeriodSnapshot:
    period_start: datetime
    period_end: datetime
    import_price_sek_kwh: float | None
    export_price_sek_kwh: float | None
    grid_import_w: float | None
    grid_export_w: float | None
    battery_soc_pct: float | None
    ev_power_w: float | None
    heartbeat_mode: str | None
    ai_decision: str | None
    heartbeat_reason: str | None
    emic_strategy_state: str | None
    emic_recommended_action: str | None


@dataclass(frozen=True, slots=True)
class DailyAuditRollup:
    day: str
    actual_energy_cost_sek: float
    baseline_cost_without_optimization_sek: float
    heartbeat_saving_sek: float
    emic_theoretical_optimal_cost_sek: float
    additional_optimization_potential_sek: float
    heartbeat_efficiency_pct: float | None
    imported_kwh: float
    exported_kwh: float
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    period_count: int


@dataclass(frozen=True, slots=True)
class MonthlyAuditRollup:
    month: str
    actual_energy_cost_sek: float
    baseline_cost_without_optimization_sek: float
    heartbeat_saving_sek: float
    emic_theoretical_optimal_cost_sek: float
    additional_optimization_potential_sek: float
    heartbeat_efficiency_pct: float | None
    imported_kwh: float
    exported_kwh: float
    days_with_data: int
