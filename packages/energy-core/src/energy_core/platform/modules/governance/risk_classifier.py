"""Risk classification for module permissions and capabilities."""

from __future__ import annotations

from energy_core.platform.modules.governance.types import RiskLevel

HIGH_RISK_PERMISSIONS = frozenset(
    {
        "device.control",
        "energy.control",
        "network.local",
    }
)

MEDIUM_RISK_PERMISSIONS = frozenset(
    {
        "network.external",
        "secrets.read_own",
    }
)

CONTROL_CAPABILITY_PREFIXES = (
    "device.control",
    "energy.control",
    "charger.command",
    "ev_charger.start",
    "ev_charger.stop",
    "ev_charger.set_current",
    "vehicle.command",
    "spa.control",
    "spa.set_temperature",
)


def is_control_capable(
    *,
    permissions: tuple[str, ...] | list[str],
    provided_capabilities: tuple[str, ...] | list[str],
) -> bool:
    perms = set(permissions)
    if perms.intersection(HIGH_RISK_PERMISSIONS):
        return True
    for cap in provided_capabilities:
        lowered = cap.lower()
        if any(lowered.startswith(prefix) for prefix in CONTROL_CAPABILITY_PREFIXES):
            return True
        if lowered in {"device.control", "energy.control"}:
            return True
    return False


def permission_risk_level(permission: str) -> RiskLevel:
    if permission in {"energy.control"}:
        return RiskLevel.CRITICAL
    if permission in HIGH_RISK_PERMISSIONS:
        return RiskLevel.HIGH
    if permission in MEDIUM_RISK_PERMISSIONS:
        return RiskLevel.NORMAL
    return RiskLevel.LOW


def highest_risk_level(permissions: tuple[str, ...] | list[str]) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.NORMAL, RiskLevel.HIGH, RiskLevel.CRITICAL]
    highest = RiskLevel.LOW
    for perm in permissions:
        level = permission_risk_level(perm)
        if order.index(level) > order.index(highest):
            highest = level
    return highest
