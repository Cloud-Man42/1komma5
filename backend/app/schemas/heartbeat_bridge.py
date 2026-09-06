from __future__ import annotations

from datetime import date, datetime
from typing import Any

from energy_core.integrations.heartbeat.connection import CLOUD_PORT, HeartbeatConnectionType
from pydantic import BaseModel, Field, field_validator

class HeartbeatDiscoveryRunResultResponse(BaseModel):
    run_id: int
    report_text: str
    setup_classification: str
    bridge_lifecycle: str
    resolved_ev_id: str | None
    confidence_pct: float
    virtual_bridge_suitable: bool
    charging_modes: list[str] = Field(default_factory=list)
    emic_vehicle_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class HeartbeatDiscoveryRunResponse(BaseModel):
    id: int
    status: str
    system_id: str | None
    conclusion_class: str | None
    bridge_lifecycle: str | None
    resolved_ev_id: str | None
    confidence_pct: float | None
    started_at: datetime
    completed_at: datetime | None


class HeartbeatDiscoveryRunDetailResponse(HeartbeatDiscoveryRunResponse):
    report_text: str
    report: dict[str, Any] = Field(default_factory=dict)
    observations: list[dict[str, Any]] = Field(default_factory=list)


class HeartbeatBridgeStatusResponse(BaseModel):
    heartbeat_connection: str
    ev_profile: str
    ev_id: str | None
    confidence_pct: float | None
    physical_hb_wallbox: str
    charge_amps_halo: str
    halo_online: bool
    virtual_bridge: str
    setup_classification: str | None
    bridge_lifecycle: str
    simulation_mode: bool
    physical_control: str
    write_enabled: bool
    settings: dict[str, Any] = Field(default_factory=dict)
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class HeartbeatEvMappingResponse(BaseModel):
    id: int
    heartbeat_ev_id: str
    heartbeat_ev_name: str
    physical_charger_id: int | None
    vehicle_id: int | None
    provider: str
    enabled: bool
    confidence_pct: float
    last_discovery_at: datetime | None


class HeartbeatEvMappingUpdateRequest(BaseModel):
    enabled: bool | None = None
    physical_charger_id: int | None = None
    vehicle_id: int | None = None


class HeartbeatBridgeSettingsResponse(BaseModel):
    site_id: int
    discovery_enabled: bool
    write_enabled: bool
    virtual_bridge_enabled: bool
    physical_control_enabled: bool
    soc_sync_enabled: bool
    replay_enabled: bool
    simulation_mode: bool
    confidence_threshold_pct: float
    battery_priority_mode: str


class HeartbeatBridgeSettingsUpdateRequest(BaseModel):
    discovery_enabled: bool | None = None
    write_enabled: bool | None = None
    virtual_bridge_enabled: bool | None = None
    physical_control_enabled: bool | None = None
    soc_sync_enabled: bool | None = None
    replay_enabled: bool | None = None
    simulation_mode: bool | None = None
    confidence_threshold_pct: float | None = Field(default=None, ge=0, le=100)
    battery_priority_mode: str | None = None


class HeartbeatWriteTestResponse(BaseModel):
    classification: str
    requested_value: Any | None = None
    http_status: int | None = None
    read_back_value: Any | None = None
    rollback_verified: bool | None = None
    duration_ms: int | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    dry_run: bool = True


class HeartbeatReplayResponse(BaseModel):
    report: dict[str, Any] = Field(default_factory=dict)
    report_text: str = ""
