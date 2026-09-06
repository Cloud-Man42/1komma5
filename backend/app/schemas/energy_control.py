from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class EnergyControlActionResponse(BaseModel):
    id: int
    recorded_at: datetime
    optimization_mode: str
    action: str
    target: str
    outcome: str
    dry_run: bool
    reason: str | None = None


class AdminAuditEntryResponse(BaseModel):
    id: int
    recorded_at: datetime
    http_method: str
    path: str
    action: str
    site_slug: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    outcome: str
    summary: dict[str, Any] | None = None


class AdminAuditLogResponse(BaseModel):
    entries: list[AdminAuditEntryResponse] = Field(default_factory=list)


class EnergyControlStatusResponse(BaseModel):
    slug: str
    timezone: str
    optimization_mode: str
    control_enabled: bool
    writes_allowed: bool
    automatic_allowed: bool
    provider: str
    last_action: EnergyControlActionResponse | None = None


class EnergyControlSettingsUpdateRequest(BaseModel):
    optimization_mode: str | None = None
    control_enabled: bool | None = None


class EnergyControlPreviewRequest(BaseModel):
    action: str
    target: str = "site"


class EnergyControlResultResponse(BaseModel):
    slug: str
    action: str
    target: str
    outcome: str
    dry_run: bool
    reason: str
    reason_sv: str
    provider: str


class EnergyControlRecentResponse(BaseModel):
    slug: str
    actions: list[EnergyControlActionResponse] = Field(default_factory=list)
