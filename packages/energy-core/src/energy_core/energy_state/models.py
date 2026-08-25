"""Normalized energy snapshot models for widget and Apple clients."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BatteryState(StrEnum):
    IDLE = "idle"
    CHARGING = "charging"
    DISCHARGING = "discharging"
    FULL = "full"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


_BATTERY_STATE_TEXT_SV: dict[BatteryState, str] = {
    BatteryState.IDLE: "Vilar",
    BatteryState.CHARGING: "Laddar",
    BatteryState.DISCHARGING: "Urladdar",
    BatteryState.FULL: "Fullt",
    BatteryState.UNAVAILABLE: "Ej tillgängligt",
    BatteryState.UNKNOWN: "Okänt",
}


class EvState(StrEnum):
    UNAVAILABLE = "unavailable"
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    WAITING = "waiting"
    SCHEDULED = "scheduled"
    CHARGING = "charging"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAULTED = "faulted"
    UNKNOWN = "unknown"


_EV_STATE_TEXT_SV: dict[EvState, str] = {
    EvState.UNAVAILABLE: "Ej tillgänglig",
    EvState.DISCONNECTED: "Frånkopplad",
    EvState.CONNECTED: "Ansluten",
    EvState.WAITING: "Väntar",
    EvState.SCHEDULED: "Schemalagd",
    EvState.CHARGING: "Laddar",
    EvState.PAUSED: "Pausad",
    EvState.COMPLETED: "Klar",
    EvState.FAULTED: "Fel",
    EvState.UNKNOWN: "Okänt",
}


class SystemStatus(StrEnum):
    ONLINE = "online"
    PARTIAL = "partial"
    OFFLINE = "offline"
    FAULT = "fault"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class DataQuality(StrEnum):
    MEASURED = "measured"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"


class SmartChargingMode(StrEnum):
    OFF = "off"
    MANUAL = "manual"
    CHEAPEST = "cheapest"
    SOLAR_ONLY = "solar_only"
    SMART = "smart"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class SmartChargingState(StrEnum):
    OFF = "off"
    MANUAL = "manual"
    CHEAPEST = "cheapest"
    SOLAR_ONLY = "solar_only"
    SMART = "smart"
    SCHEDULED = "scheduled"
    EMERGENCY = "emergency"
    WAITING_FOR_SURPLUS = "waiting_for_surplus"
    UNKNOWN = "unknown"


def battery_state_text_sv(state: BatteryState) -> str:
    return _BATTERY_STATE_TEXT_SV.get(state, "Okänt")


def ev_state_text_sv(state: EvState) -> str:
    return _EV_STATE_TEXT_SV.get(state, "Okänt")


@dataclass(frozen=True, slots=True)
class EnergySiteSnapshot:
    site_id: int
    site_slug: str
    site_name: str
    timezone: str

    solar_power_kw: float | None
    solar_energy_today_kwh: float | None

    house_power_kw: float | None
    house_energy_today_kwh: float | None

    grid_power_kw: float | None
    grid_import_power_kw: float | None
    grid_export_power_kw: float | None
    grid_import_today_kwh: float | None
    grid_export_today_kwh: float | None

    battery_soc_percent: float | None
    battery_power_kw: float | None
    battery_state: BatteryState
    battery_state_text_sv: str
    battery_energy_charged_today_kwh: float | None
    battery_energy_discharged_today_kwh: float | None

    ev_state: EvState
    ev_state_text_sv: str
    ev_power_kw: float | None
    ev_energy_today_kwh: float | None

    current_electricity_price: float | None
    current_electricity_price_including_fees: float | None

    saved_today_sek: float | None
    saved_month_sek: float | None
    economic_data_quality: DataQuality

    self_consumption_percent: float | None
    self_sufficiency_percent: float | None

    operating_mode: str | None
    decision_text: str

    smart_charging_mode: SmartChargingMode | None
    smart_charging_state: SmartChargingState | None
    smart_charging_decision_text: str | None

    system_status: SystemStatus

    updated_at: datetime | None
    data_age_seconds: int | None
    is_stale: bool
