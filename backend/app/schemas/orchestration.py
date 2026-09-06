from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class EnergyOrchestrationLoadResponse(BaseModel):
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
    reason_sv: str | None = None
    explanation_sv: str | None = None
    dry_run: bool = True


class EnergyOrchestrationResponse(BaseModel):
    site_slug: str
    loads: list[EnergyOrchestrationLoadResponse] = Field(default_factory=list)


class EnergyOrchestrationPriorityItem(BaseModel):
    load_id: str
    priority: int = Field(ge=0, le=100)


class EnergyOrchestrationPrioritiesUpdateRequest(BaseModel):
    loads: list[EnergyOrchestrationPriorityItem] = Field(default_factory=list)
