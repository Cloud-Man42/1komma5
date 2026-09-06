"""Device capability model derived from framework ChargerCapabilities."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from energy_core.chargers.framework.models import ChargerCapabilities


class DeviceCapability(StrEnum):
    READ_STATUS = "read_status"
    START = "start"
    STOP = "stop"
    READ_POWER = "read_power"
    READ_ENERGY = "read_energy"
    READ_SESSION = "read_session"
    READ_ACTUAL_CURRENT = "read_actual_current"
    SET_CURRENT = "set_current"
    READ_PER_PHASE_CURRENT = "read_per_phase_current"
    READ_METER_VALUES = "read_meter_values"
    READ_LOAD_BALANCER_STATE = "read_load_balancer_state"
    SET_CHARGING_PROFILE = "set_charging_profile"
    DYNAMIC_CURRENT = "dynamic_current"
    DYNAMIC_PHASE_SWITCHING = "dynamic_phase_switching"
    LOCAL_CONTROL = "local_control"
    CLOUD_CONTROL = "cloud_control"
    OCPP = "ocpp"
    MODBUS = "modbus"
    SMART_CHARGING = "smart_charging"


_CAPABILITY_FIELD_MAP: dict[DeviceCapability, tuple[str, ...]] = {
    DeviceCapability.READ_STATUS: ("can_read_status",),
    DeviceCapability.START: ("can_start_charging", "supports_remote_start_stop"),
    DeviceCapability.STOP: ("can_stop_charging", "supports_remote_start_stop"),
    DeviceCapability.READ_POWER: ("can_read_power", "supports_power_reading"),
    DeviceCapability.READ_ENERGY: ("can_read_energy",),
    DeviceCapability.READ_SESSION: ("can_read_session",),
    DeviceCapability.READ_ACTUAL_CURRENT: ("can_read_actual_current",),
    DeviceCapability.SET_CURRENT: ("can_set_max_current", "supports_current_control"),
    DeviceCapability.READ_PER_PHASE_CURRENT: ("can_read_per_phase_current",),
    DeviceCapability.READ_METER_VALUES: ("can_read_meter_values",),
    DeviceCapability.READ_LOAD_BALANCER_STATE: ("can_read_load_balancer_state",),
    DeviceCapability.SET_CHARGING_PROFILE: ("can_set_charging_profile",),
    DeviceCapability.DYNAMIC_CURRENT: ("supports_dynamic_current",),
    DeviceCapability.DYNAMIC_PHASE_SWITCHING: (
        "supports_dynamic_phase_switching",
        "supports_dynamic_phases",
    ),
    DeviceCapability.LOCAL_CONTROL: ("supports_local_control",),
    DeviceCapability.CLOUD_CONTROL: ("supports_cloud_control",),
    DeviceCapability.OCPP: ("supports_ocpp",),
    DeviceCapability.MODBUS: ("supports_modbus",),
    DeviceCapability.SMART_CHARGING: ("supports_smart_charging",),
}


def supports(caps: ChargerCapabilities, capability: DeviceCapability) -> bool:
    """Return True when the given capability dataclass supports the requested capability."""
    fields = _CAPABILITY_FIELD_MAP.get(capability, ())
    return any(getattr(caps, field_name, False) for field_name in fields)
