"""Vendor-neutral charger integration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

ChargerProtocol = Literal[
    "REST",
    "CLOUD_API",
    "LOCAL_HTTP",
    "OCPP_1_5",
    "OCPP_1_6J",
    "OCPP_2_0_1",
    "MODBUS_TCP",
    "MQTT",
    "UDP",
    "ZIGBEE",
    "BLUETOOTH",
    "PARTNER_API",
]

SupportLevel = Literal[
    "FULL",
    "PARTIAL",
    "EXPERIMENTAL",
    "MONITORING_ONLY",
    "UNSUPPORTED",
]

IntegrationSupportLevel = SupportLevel

ChargerState = Literal[
    "AVAILABLE",
    "CONNECTED",
    "CHARGING",
    "PAUSED",
    "FAULT",
    "OFFLINE",
    "UNKNOWN",
]

ConnectionTestStatus = Literal[
    "CONNECTED",
    "AUTH_FAILED",
    "DEVICE_NOT_FOUND",
    "TIMEOUT",
    "PROTOCOL_ERROR",
    "UNSUPPORTED",
    "UNKNOWN_ERROR",
]

ChargerErrorCode = Literal[
    "AUTH_ERROR",
    "CONNECTION_FAILED",
    "TIMEOUT",
    "RATE_LIMITED",
    "DEVICE_OFFLINE",
    "COMMAND_REJECTED",
    "UNSUPPORTED_OPERATION",
    "INVALID_RESPONSE",
    "PROTOCOL_ERROR",
    "UNKNOWN",
]

DataQuality = Literal["MEASURED", "CALCULATED", "ESTIMATED", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class CredentialFieldDefinition:
    key: str
    label: str
    field_type: Literal["text", "password", "number"] = "text"
    required: bool = True
    placeholder: str | None = None
    help_text: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionFieldDefinition:
    key: str
    label: str
    field_type: Literal["text", "number", "select", "hostname", "port"] = "text"
    required: bool = True
    placeholder: str | None = None
    help_text: str | None = None
    options: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChargerIntegrationMethodDefinition:
    id: str
    label: str
    protocol: ChargerProtocol
    connection_type: Literal["LOCAL", "CLOUD", "OCPP"]
    recommended: bool = False
    priority: int = 100
    credential_fields: tuple[CredentialFieldDefinition, ...] = ()
    connection_fields: tuple[ConnectionFieldDefinition, ...] = ()
    documentation_url: str | None = None
    implementation_status: SupportLevel = "UNSUPPORTED"
    cloud_dependent: bool = False


@dataclass(frozen=True, slots=True)
class ChargerCapabilities:
    min_current_a: float = 6.0
    max_current_a: float = 16.0
    phases: int | None = 3
    can_read_status: bool = True
    can_start_charging: bool = False
    can_stop_charging: bool = False
    can_read_power: bool = False
    can_read_energy: bool = False
    can_read_session: bool = False
    can_read_actual_current: bool = False
    can_set_max_current: bool = False
    can_read_per_phase_current: bool = False
    can_read_meter_values: bool = False
    can_read_load_balancer_state: bool = False
    can_set_charging_profile: bool = False
    supports_dynamic_current: bool = False
    supports_dynamic_phase_switching: bool = False
    supports_local_control: bool = False
    supports_cloud_control: bool = False
    supports_ocpp: bool = False
    supports_modbus: bool = False
    supports_smart_charging: bool = False
    # Legacy aliases used by existing code
    supports_current_control: bool = False
    supports_remote_start_stop: bool = False
    supports_power_reading: bool = False
    supports_dynamic_phases: bool = False

    @classmethod
    def from_legacy(
        cls,
        *,
        min_current_a: float,
        max_current_a: float,
        phases: int | None,
        supports_current_control: bool,
        supports_remote_start_stop: bool,
        supports_power_reading: bool,
        supports_dynamic_phases: bool,
    ) -> ChargerCapabilities:
        return cls(
            min_current_a=min_current_a,
            max_current_a=max_current_a,
            phases=phases,
            can_read_status=True,
            can_start_charging=supports_remote_start_stop,
            can_stop_charging=supports_remote_start_stop,
            can_read_power=supports_power_reading,
            can_read_actual_current=supports_power_reading,
            can_set_max_current=supports_current_control,
            supports_dynamic_current=supports_current_control,
            supports_remote_start_stop=supports_remote_start_stop,
            supports_current_control=supports_current_control,
            supports_power_reading=supports_power_reading,
            supports_dynamic_phases=supports_dynamic_phases,
            supports_smart_charging=supports_current_control and supports_remote_start_stop,
        )


@dataclass(frozen=True, slots=True)
class ChargerModelDefinition:
    id: str
    manufacturer_id: str
    name: str
    supported_protocols: tuple[ChargerProtocol, ...]
    capabilities: ChargerCapabilities
    integration_methods: tuple[str, ...]
    status: SupportLevel
    documentation_url: str | None = None
    api_documentation_url: str | None = None
    protocol_documentation_url: str | None = None


@dataclass(frozen=True, slots=True)
class ChargerManufacturerDefinition:
    id: str
    name: str
    models: tuple[ChargerModelDefinition, ...]


@dataclass(frozen=True, slots=True)
class NormalizedChargerStatus:
    online: bool
    vehicle_connected: bool
    charging: bool
    state: ChargerState
    requested_current_a: float | None = None
    actual_current_a: float | None = None
    configured_current_a: float | None = None
    power_w: float | None = None
    session_energy_kwh: float | None = None
    error_code: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class ChargerStatus:
    """Backward-compatible status DTO used by smart charging."""

    connected: bool
    vehicle_connected: bool
    current_limit_a: float | None
    charging: bool

    @classmethod
    def from_normalized(cls, status: NormalizedChargerStatus) -> ChargerStatus:
        return cls(
            connected=status.online,
            vehicle_connected=status.vehicle_connected,
            current_limit_a=status.configured_current_a or status.requested_current_a,
            charging=status.charging,
        )


@dataclass(frozen=True, slots=True)
class DetectedDevice:
    vendor: str | None = None
    model: str | None = None
    serial_number: str | None = None
    firmware: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectionTestResult:
    success: bool
    status: ConnectionTestStatus
    message: str
    detected_device: DetectedDevice | None = None
    capabilities: ChargerCapabilities | None = None
    model_mismatch: bool = False
    detected_model_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChargingSession:
    charger_id: str
    started_at: datetime
    ended_at: datetime | None = None
    energy_kwh: float | None = None
    start_meter_kwh: float | None = None
    stop_meter_kwh: float | None = None
    peak_power_kw: float | None = None
    quality: DataQuality = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class MeterValues:
    power_w: float | None = None
    energy_kwh: float | None = None
    phase_current_l1_a: float | None = None
    phase_current_l2_a: float | None = None
    phase_current_l3_a: float | None = None
    quality: DataQuality = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ChargerConfiguration:
    charger_id: int
    site_id: int
    manufacturer_id: str
    model_id: str
    integration_method: str
    display_name: str
    enabled: bool = True
    external_charger_id: str | None = None
    api_key: str | None = None
    connection_settings: dict[str, Any] = field(default_factory=dict)
    min_current_a: float = 6.0
    max_current_a: float = 16.0
    phases: int = 3
    nominal_voltage_v: float = 230.0
    legacy_control_source: str | None = None


@runtime_checkable
class ChargerAdapter(Protocol):
    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def get_status(self) -> NormalizedChargerStatus: ...

    async def get_legacy_status(self) -> ChargerStatus: ...

    async def get_capabilities(self) -> ChargerCapabilities: ...

    async def start_charging(self) -> None: ...

    async def stop_charging(self) -> None: ...

    async def get_requested_current(self) -> float | None: ...

    async def get_actual_current(self) -> float | None: ...

    async def set_max_current(self, amps: float) -> None: ...

    async def get_power(self) -> float | None: ...

    async def get_energy(self) -> float | None: ...

    async def get_session(self) -> ChargingSession | None: ...

    async def test_connection(self) -> ConnectionTestResult: ...

    async def get_meter_values(self) -> MeterValues | None: ...


@runtime_checkable
class MeterReader(Protocol):
    async def get_snapshot(self): ...
