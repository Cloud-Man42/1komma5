"""Normalized vehicle domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class VehicleConnectionState(StrEnum):
    DISCONNECTED = "DISCONNECTED"
    AUTHENTICATING = "AUTHENTICATING"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    REFRESHING_TOKEN = "REFRESHING_TOKEN"
    RECONNECTING = "RECONNECTING"
    BACKOFF = "BACKOFF"
    DEGRADED = "DEGRADED"


class DataQuality(StrEnum):
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


class ValueQuality(StrEnum):
    LIVE = "LIVE"
    RECENT = "RECENT"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class VehicleCapabilities:
    can_read_soc: bool = False
    can_read_range: bool = False
    can_read_charging_state: bool = False
    can_read_charging_power: bool = False
    can_read_target_soc: bool = False
    can_read_departure_time: bool = False
    can_set_target_soc: bool = False
    can_start_charging: bool = False
    can_stop_charging: bool = False


@dataclass(frozen=True, slots=True)
class TimedValue:
    value: float | bool | str | None
    source_timestamp: datetime | None
    received_timestamp: datetime | None
    age_seconds: float | None
    quality: ValueQuality


@dataclass(frozen=True, slots=True)
class VehicleState:
    vehicle_id: str
    provider: str
    manufacturer: str
    model: str
    vin: str | None = None
    state_of_charge_percent: float | None = None
    target_soc_percent: float | None = None
    electric_range_km: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_timestamp: datetime | None = None
    is_plugged_in: bool | None = None
    is_charging: bool | None = None
    charging_power_kw: float | None = None
    charging_power_limit_kw: float | None = None
    estimated_charge_complete_at: datetime | None = None
    departure_time: datetime | None = None
    odometer_km: float | None = None
    connection_state: VehicleConnectionState = VehicleConnectionState.DISCONNECTED
    data_quality: DataQuality = DataQuality.UNKNOWN
    last_vehicle_update: datetime | None = None
    last_provider_update: datetime | None = None
    soc_quality: DataQuality = DataQuality.UNKNOWN
    charging_power_quality: DataQuality = DataQuality.UNKNOWN
    range_quality: DataQuality = DataQuality.UNKNOWN
    capabilities: VehicleCapabilities = field(default_factory=VehicleCapabilities)


@dataclass(frozen=True, slots=True)
class VehicleStateChangedEvent:
    state: VehicleState
    previous_state: VehicleState | None = None


@dataclass(frozen=True, slots=True)
class VehicleCommandResult:
    success: bool
    message: str
    vehicle_id: str
    command: str
