from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class HeartbeatAuditRollupResponse(BaseModel):
    actual_energy_cost_sek: float
    baseline_cost_without_optimization_sek: float
    heartbeat_saving_sek: float
    emic_theoretical_optimal_cost_sek: float
    additional_optimization_potential_sek: float
    heartbeat_efficiency_pct: float | None = None
    imported_kwh: float
    exported_kwh: float


class HeartbeatAuditPeriodSnapshotResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    import_price_sek_kwh: float | None = None
    export_price_sek_kwh: float | None = None
    grid_import_w: float | None = None
    grid_export_w: float | None = None
    battery_soc_pct: float | None = None
    ev_power_w: float | None = None
    heartbeat_mode: str | None = None
    ai_decision: str | None = None
    heartbeat_reason: str | None = None
    emic_strategy_state: str | None = None
    emic_recommended_action: str | None = None


class HeartbeatAuditDailyResponse(BaseModel):
    slug: str
    timezone: str
    day: str
    rollup: HeartbeatAuditRollupResponse
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    period_count: int
    periods: list[HeartbeatAuditPeriodSnapshotResponse] = Field(default_factory=list)


class HeartbeatAuditMonthlyResponse(BaseModel):
    slug: str
    timezone: str
    month: str
    rollup: HeartbeatAuditRollupResponse
    days_with_data: int
    daily: list[HeartbeatAuditDailyResponse] = Field(default_factory=list)
