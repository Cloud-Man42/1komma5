from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class ForecastMetricSummaryResponse(BaseModel):
    kind: str
    mae: float | None = None
    bias: float | None = None
    sample_count: int = 0
    mape_pct: float | None = None


class ForecastSnapshotResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    kind: str
    predicted_value: float
    actual_value: float | None = None
    forecast_recorded_at: datetime
    actual_recorded_at: datetime | None = None
    model_version: str | None = None


class ForecastLearningSummaryResponse(BaseModel):
    slug: str
    timezone: str
    days: int
    metrics: list[ForecastMetricSummaryResponse] = Field(default_factory=list)
    last_reconciled_at: datetime | None = None


class ForecastLearningRecentResponse(BaseModel):
    slug: str
    timezone: str
    kind: str | None = None
    snapshots: list[ForecastSnapshotResponse] = Field(default_factory=list)
