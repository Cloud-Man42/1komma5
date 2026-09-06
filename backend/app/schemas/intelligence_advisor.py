from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class BatteryOpportunityResponse(BaseModel):
    slug: str
    timezone: str
    available: bool
    monitor_only: bool = True
    unavailable_reason_sv: str | None = None
    action: str | None = None
    action_label_sv: str | None = None
    headline_sv: str | None = None
    reason_sv: str | None = None
    confidence: float | None = None
    battery_soc_pct: float | None = None
    recommended_reserve_soc_pct: float | None = None
    expected_value_sek_kwh: float | None = None
    next_peak_at: datetime | None = None
    next_peak_import_sek_kwh: float | None = None
    optimization_mode: str | None = None
    strategy_state: str | None = None


class HorizonLoadRecommendationResponse(BaseModel):
    load_id: str
    name: str
    load_type: str
    priority: int
    strategy: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    expected_energy_kwh: float | None = None
    expected_cost_sek: float | None = None
    expected_energy_source: str | None = None
    savings_sek: float | None = None
    reason_sv: str | None = None
    explanation_sv: str | None = None


class HorizonOptimizerResponse(BaseModel):
    slug: str
    timezone: str
    available: bool
    monitor_only: bool = True
    unavailable_reason_sv: str | None = None
    horizon_hours: int
    horizon_blocks: int
    generated_at: datetime | None = None
    total_planned_savings_sek: float | None = None
    headline_sv: str | None = None
    summary_sv: str | None = None
    loads: list[HorizonLoadRecommendationResponse] = Field(default_factory=list)
    battery: BatteryOpportunityResponse | None = None
