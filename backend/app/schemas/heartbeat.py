from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator


class SiteHeartbeatMappingResponse(BaseModel):
    slug: str
    name: str
    external_system_id: str | None = None


class SiteHeartbeatMappingUpdate(BaseModel):
    slug: str
    external_system_id: str | None = None


class HeartbeatConfigResponse(BaseModel):
    connection_type: str
    connection_type_label: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    poll_interval_seconds: int
    dashboard_refresh_seconds: int
    api_url: str | None = None
    username: str = ""
    password_configured: bool
    api_token_configured: bool
    connection_mode: str
    contacting_component: str
    implementation_status: str
    notes: list[str] = Field(default_factory=list)
    sites: list[SiteHeartbeatMappingResponse] = Field(default_factory=list)
    updated_at: datetime | None = None


class HeartbeatConfigUpdateRequest(BaseModel):
    connection_type: HeartbeatConnectionType
    host: str = ""
    port: int = Field(default=CLOUD_PORT, ge=1, le=65535)
    use_tls: bool = True
    api_path: str = "/api"
    poll_interval_seconds: int = Field(default=60, ge=5, le=3600)
    dashboard_refresh_seconds: int = Field(default=30, ge=1, le=30)
    username: str = ""
    password: str | None = None
    api_token: str | None = None
    sites: list[SiteHeartbeatMappingUpdate] = Field(default_factory=list)

    @field_validator("connection_type", mode="before")
    @classmethod
    def normalize_connection_type(cls, value: str | HeartbeatConnectionType) -> HeartbeatConnectionType:
        if isinstance(value, HeartbeatConnectionType):
            return value
        return HeartbeatConnectionType(str(value).lower())

    @field_validator("host", "username", "api_path", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str:
        return (value or "").strip()


class ChargeAmpsConfigResponse(BaseModel):
    provider: str
    effective_provider: str
    mock: bool
    api_key_configured: bool
    env_api_key_configured: bool
    charger_api_keys_configured: int = 0
    email_configured: bool
    password_configured: bool
    ready: bool
    notes: list[str] = Field(default_factory=list)


class TimescaleHypertableCompressionStatus(BaseModel):
    compression_enabled: bool
    policy: str


class TimescalePolicyStatusResponse(BaseModel):
    status: str
    reason: str | None = None
    retention_enabled: bool
    compression_enabled: bool
    retention: dict[str, str] = Field(default_factory=dict)
    compression: dict[str, TimescaleHypertableCompressionStatus] = Field(default_factory=dict)


class ChargerReadinessIssueResponse(BaseModel):
    site_slug: str
    charger_id: int
    charger_name: str
    code: str
    message: str


class ChargingReadinessResponse(BaseModel):
    ready: bool
    chargeamps_ready: bool
    active_bridge_chargers: int
    issues: list[ChargerReadinessIssueResponse] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
