"""Human-readable capability and permission labels (backend authoritative)."""

from __future__ import annotations

from energy_core.platform.modules.governance.risk_classifier import permission_risk_level
from energy_core.platform.modules.governance.types import RiskLevel

_CAPABILITY_LABELS: dict[str, str] = {
    "energy.read_grid_power": "Reads grid power",
    "energy.read_solar_power": "Reads solar production",
    "battery.read_soc": "Reads battery state of charge",
    "battery.read_power": "Reads battery power",
    "ev_charger.start": "Controls charging start",
    "ev_charger.stop": "Controls charging stop",
    "ev_charger.set_current": "Changes charging current",
    "ev_charger.read_power": "Reads charging power",
    "ev_charger.read_energy": "Reads charging energy",
    "vehicle.read_soc": "Reads vehicle battery level",
    "vehicle.read_range": "Reads vehicle range",
    "vehicle.read_charging_state": "Reads vehicle charging state",
    "spa.read_temperature": "Reads spa temperature",
    "spa.set_temperature": "Controls spa temperature",
    "price.read_current": "Reads current electricity price",
    "price.read_forecast": "Reads price forecast",
    "weather.read_current": "Reads current weather",
    "weather.read_forecast": "Reads weather forecast",
    "forecast.solar": "Solar production forecast",
    "optimization.energy": "Energy optimization",
    "smart_charging": "Smart charging",
    "read_status": "Reads device status",
    "read_power": "Reads power",
    "device.read": "Reads device data",
    "telemetry.publish": "Publishes telemetry",
    "device.control": "Controls devices",
    "energy.control": "Controls energy equipment",
}

_PERMISSION_LABELS: dict[str, str] = {
    "network.external": "Network access to external APIs",
    "network.local": "Network access to local devices",
    "secrets.read_own": "Access module credentials",
    "device.control": "Control physical devices",
    "energy.control": "Control energy equipment",
    "filesystem.read": "Read local files",
    "filesystem.write": "Write local files",
}

_PERMISSION_GROUPS: dict[str, str] = {
    "network.external": "Network",
    "network.local": "Network",
    "secrets.read_own": "Secrets",
    "device.control": "Device control",
    "energy.control": "Device control",
    "filesystem.read": "System",
    "filesystem.write": "System",
}


def capability_label(capability: str) -> str:
    return _CAPABILITY_LABELS.get(capability, capability.replace(".", " ").replace("_", " ").title())


def permission_label(permission: str) -> str:
    return _PERMISSION_LABELS.get(permission, permission.replace(".", " ").replace("_", " ").title())


def permission_group(permission: str) -> str:
    return _PERMISSION_GROUPS.get(permission, "Read access")


def permission_view(permission: str) -> tuple[str, str, str]:
    risk = permission_risk_level(permission)
    group = permission_group(permission)
    if risk == RiskLevel.CRITICAL:
        group = "Device control"
    elif risk == RiskLevel.HIGH and group == "Read access":
        group = "Device control"
    return permission_label(permission), risk.value, group
