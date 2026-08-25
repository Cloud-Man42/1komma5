"""Data models for Heartbeat EV discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SetupClassification(StrEnum):
    FULL_NATIVE_HEARTBEAT_EV = "A"
    HEARTBEAT_EV_WITHOUT_WALLBOX = "B"
    VIRTUAL_CHARGER_BRIDGE_READY = "C"
    EV_ID_NOT_FOUND = "D"
    AMBIGUOUS_EV_MAPPING = "E"
    HEARTBEAT_WRITE_NOT_SUPPORTED = "F"
    HEARTBEAT_AUTH_FAILED = "G"


class BridgeLifecycleState(StrEnum):
    DISABLED = "DISABLED"
    DISCOVERY = "DISCOVERY"
    READY = "READY"
    VIRTUAL_CHARGER_BRIDGE_CANDIDATE = "VIRTUAL_CHARGER_BRIDGE_CANDIDATE"
    VEHICLE_NOT_CONNECTED = "VEHICLE_NOT_CONNECTED"
    SIMULATION = "SIMULATION"
    FAILSAFE = "FAILSAFE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


@dataclass(frozen=True, slots=True)
class HeartbeatApiObservation:
    method: str
    path: str
    status_code: int
    started_at: datetime
    duration_ms: int
    request_headers_redacted: dict[str, str]
    response_headers_redacted: dict[str, str]
    raw_json: dict[str, Any] | list[Any] | None
    parsed_summary: dict[str, Any]
    unknown_fields: tuple[str, ...]
    schema_fingerprint: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EvProfileDiscovery:
    heartbeat_ev_id: str
    name: str
    manufacturer: str
    model: str
    battery_capacity_kwh: float | None
    current_soc_pct: float | None
    target_soc_pct: float | None
    charging_mode: str | None
    departure_time: str | None
    assigned_charger_id: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WallboxDiscovery:
    heartbeat_charger_id: str
    gridx_hardware_id: str | None
    name: str
    manufacturer: str
    model: str
    assigned_ev_id: str | None
    status: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EmsDeviceDiscovery:
    device_id: str
    device_type: str
    label: str
    ev_related: bool
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EvAssignmentDiscovery:
    ev_id: str
    charger_id: str | None
    source: str
    matched: bool


@dataclass(frozen=True, slots=True)
class ResolvedEvId:
    heartbeat_ev_id: str | None
    confidence_pct: float
    source: str
    ev_name: str | None
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HeartbeatEvDiscoveryResult:
    site_slug: str
    site_name: str
    system_id: str | None
    authenticated: bool
    ev_profiles: tuple[EvProfileDiscovery, ...]
    wallboxes: tuple[WallboxDiscovery, ...]
    ems_devices: tuple[EmsDeviceDiscovery, ...]
    assignments: tuple[EvAssignmentDiscovery, ...]
    charging_modes: tuple[str, ...]
    ai_decision_types: tuple[str, ...]
    ai_decisions_found: bool
    resolved_ev_id: ResolvedEvId
    setup_classification: SetupClassification
    bridge_lifecycle: BridgeLifecycleState
    halo_found: bool
    halo_online: bool
    virtual_bridge_suitable: bool
    warnings: tuple[str, ...]
    observations: tuple[HeartbeatApiObservation, ...]
    field_hints: tuple[str, ...]
    started_at: datetime
    completed_at: datetime
    report_text: str = ""
    emic_vehicle_lines: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HeartbeatIntent:
    charge_requested: bool
    preferred_source: str | None
    charging_mode: str
    target_soc_pct: float | None
    departure_time: str | None
    ai_reason: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    confidence: float
    raw_decision_type: str | None = None


@dataclass(frozen=True, slots=True)
class HaloCommand:
    action: str
    current_a: float | None
    reason: str
    simulated: bool = False


@dataclass(frozen=True, slots=True)
class VirtualEvMappingRecord:
    id: int
    site_id: int
    heartbeat_ev_id: str
    heartbeat_ev_name: str
    physical_charger_id: int | None
    vehicle_id: int | None
    provider: str
    enabled: bool
    confidence_pct: float
    last_discovery_at: datetime | None


@dataclass(frozen=True, slots=True)
class HeartbeatBridgeSettingsRecord:
    site_id: int
    discovery_enabled: bool = True
    write_enabled: bool = False
    virtual_bridge_enabled: bool = False
    physical_control_enabled: bool = False
    soc_sync_enabled: bool = False
    replay_enabled: bool = True
    simulation_mode: bool = True
    confidence_threshold_pct: float = 90.0
    battery_priority_mode: str = "BATTERY_FIRST"


@dataclass
class WriteTestResult:
    classification: str
    requested_value: Any = None
    http_status: int | None = None
    read_back_value: Any = None
    rollback_value: Any = None
    rollback_verified: bool | None = None
    duration_ms: int | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)
