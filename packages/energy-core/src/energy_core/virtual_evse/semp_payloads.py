"""SEMP HTTP payload builders (pure logic)."""

from __future__ import annotations

from typing import Any

from energy_core.virtual_evse.device_profile import VirtualEvseDeviceProfile
from energy_core.virtual_evse.state import VirtualEvseState


def build_device_list(device_ids: list[str]) -> dict[str, Any]:
    return {"devices": device_ids}


def build_device_info(profile: VirtualEvseDeviceProfile) -> dict[str, Any]:
    return {
        "deviceId": profile.device_id,
        "deviceName": profile.device_name,
        "deviceType": "EVCharger",
        "deviceSerial": profile.device_id,
        "deviceVendor": "EMIC",
        "deviceModel": "Virtual EVSE",
        "maxPowerConsumption": int(profile.max_power_w),
        "minPowerConsumption": 0,
        "maxPowerProduction": 0,
    }


def build_device_status(state: VirtualEvseState) -> dict[str, Any]:
    power = int(state.reported_power_w or 0)
    ts = state.recorded_at.isoformat().replace("+00:00", "Z")
    return {
        "deviceId": state.device_id,
        "emSignalsAccepted": "No",
        "powerConsumption": {
            "powerInfo": [{"averagePower": power, "timestamp": ts}],
        },
        "status": state.status.value,
        "timestamp": ts,
    }


def build_device2em(state: VirtualEvseState) -> dict[str, Any]:
    return build_device_status(state)
