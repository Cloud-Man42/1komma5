"""Publisher permission allowlist and capability policy."""

from __future__ import annotations

from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.packages.errors import INVALID_CAPABILITY, PackageError

ALLOWED_PERMISSIONS = frozenset(
    {
        "network.external",
        "network.local",
        "device.read",
        "device.control",
        "vehicle.location",
        "filesystem.module_data",
        "secrets.read_own",
    }
)

INVALID_PERMISSION = "INVALID_PERMISSION"
PERMISSION_CAPABILITY_MISMATCH = "PERMISSION_CAPABILITY_MISMATCH"

_CONTROL_CAPABILITIES = frozenset(
    {
        Capability.EV_CHARGER_START,
        Capability.EV_CHARGER_STOP,
        Capability.EV_CHARGER_SET_CURRENT,
        Capability.SPA_SET_TEMPERATURE,
        Capability.OPTIMIZATION_ENERGY,
        Capability.SMART_CHARGING,
    }
)

_READ_CAPABILITIES = frozenset(
    {
        Capability.READ_STATUS,
        Capability.READ_POWER,
        Capability.VEHICLE_READ_SOC,
        Capability.VEHICLE_READ_RANGE,
        Capability.VEHICLE_READ_CHARGING_STATE,
    }
)


def validate_permissions(permissions: tuple[str, ...]) -> None:
    unknown = [p for p in permissions if p not in ALLOWED_PERMISSIONS]
    if unknown:
        raise PackageError(
            f"unknown permissions: {', '.join(unknown)}",
            code=INVALID_PERMISSION,
        )


def validate_capability_permissions(
    *,
    provided: tuple[str, ...],
    permissions: tuple[str, ...],
) -> None:
    permission_set = set(permissions)
    for cap_name in provided:
        try:
            cap = Capability(cap_name)
        except ValueError as exc:
            raise PackageError(f"unknown capability: {cap_name}", code=INVALID_CAPABILITY) from exc
        if cap in _CONTROL_CAPABILITIES and "device.control" not in permission_set:
            raise PackageError(
                f"capability {cap_name} requires device.control permission",
                code=PERMISSION_CAPABILITY_MISMATCH,
            )
        if cap in _READ_CAPABILITIES and "device.read" not in permission_set:
            raise PackageError(
                f"capability {cap_name} requires device.read permission",
                code=PERMISSION_CAPABILITY_MISMATCH,
            )
