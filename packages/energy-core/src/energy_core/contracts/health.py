"""Unified health status and mappers from domain-specific enums."""

from __future__ import annotations

from enum import StrEnum


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


def from_vehicle_integration_status(status: str) -> HealthStatus:
    """Map vehicles.health.IntegrationHealthStatus values."""
    mapping = {
        "CONNECTED": HealthStatus.HEALTHY,
        "DEGRADED": HealthStatus.DEGRADED,
        "OFFLINE": HealthStatus.UNAVAILABLE,
        "AUTHENTICATION_REQUIRED": HealthStatus.UNAVAILABLE,
        "MERCEDES_BACKEND_UNAVAILABLE": HealthStatus.UNAVAILABLE,
        "VEHICLE_SLEEPING": HealthStatus.DEGRADED,
        "DATA_STALE": HealthStatus.DEGRADED,
    }
    return mapping.get(status, HealthStatus.UNAVAILABLE)


def from_energy_provider_status(status: str) -> HealthStatus:
    """Map energy.unified.ProviderHealthStatus values."""
    mapping = {
        "ok": HealthStatus.HEALTHY,
        "stale": HealthStatus.DEGRADED,
        "degraded": HealthStatus.DEGRADED,
        "error": HealthStatus.UNAVAILABLE,
        "unknown": HealthStatus.UNAVAILABLE,
    }
    return mapping.get(status.lower(), HealthStatus.UNAVAILABLE)


def from_solar_intelligence_status(status: str) -> HealthStatus:
    """Map solar_intelligence.types.ProviderHealthStatus values."""
    mapping = {
        "HEALTHY": HealthStatus.HEALTHY,
        "DEGRADED": HealthStatus.DEGRADED,
        "UNAVAILABLE": HealthStatus.UNAVAILABLE,
        "UNKNOWN": HealthStatus.UNAVAILABLE,
    }
    return mapping.get(status, HealthStatus.UNAVAILABLE)


def from_chargefinder_status(status: str) -> HealthStatus:
    """Map chargefinder_health.ChargeFinderHealthStatus values."""
    mapping = {
        "AVAILABLE": HealthStatus.HEALTHY,
        "DEGRADED": HealthStatus.DEGRADED,
        "BLOCKED": HealthStatus.UNAVAILABLE,
        "UNAVAILABLE": HealthStatus.UNAVAILABLE,
        "DISABLED": HealthStatus.DISABLED,
    }
    return mapping.get(status, HealthStatus.UNAVAILABLE)


def from_vehicle_summary_health(status: str) -> HealthStatus:
    """Map coarse vehicle integration summary values (HEALTHY/DEGRADED/UNHEALTHY)."""
    mapping = {
        "HEALTHY": HealthStatus.HEALTHY,
        "DEGRADED": HealthStatus.DEGRADED,
        "UNHEALTHY": HealthStatus.UNAVAILABLE,
    }
    return mapping.get(status, HealthStatus.UNAVAILABLE)


def from_spa_health(
    *,
    integration_enabled: bool,
    api_status: str,
    spa_status: str,
    integration_degraded: bool,
) -> HealthStatus:
    """Map spa health panel fields to unified HealthStatus."""
    if not integration_enabled or api_status == "DISABLED":
        return HealthStatus.DISABLED
    if integration_degraded:
        return HealthStatus.DEGRADED
    if api_status == "ERROR":
        return HealthStatus.UNAVAILABLE
    if spa_status == "ONLINE":
        return HealthStatus.HEALTHY
    if api_status == "OK":
        return HealthStatus.DEGRADED
    return HealthStatus.UNAVAILABLE


def aggregate_health_status(statuses: tuple[HealthStatus, ...]) -> HealthStatus:
    """Roll up provider-level statuses into a single site-level status."""
    if not statuses:
        return HealthStatus.UNAVAILABLE
    if all(status == HealthStatus.HEALTHY for status in statuses):
        return HealthStatus.HEALTHY
    if any(status == HealthStatus.HEALTHY for status in statuses):
        return HealthStatus.DEGRADED
    if any(status == HealthStatus.DISABLED for status in statuses):
        return HealthStatus.DISABLED
    return HealthStatus.UNAVAILABLE


def to_vehicle_integration_status(status: HealthStatus) -> str:
    """Best-effort reverse mapping for API compatibility."""
    mapping = {
        HealthStatus.HEALTHY: "CONNECTED",
        HealthStatus.DEGRADED: "DEGRADED",
        HealthStatus.UNAVAILABLE: "OFFLINE",
        HealthStatus.DISABLED: "OFFLINE",
    }
    return mapping[status]


def to_energy_provider_status(status: HealthStatus) -> str:
    mapping = {
        HealthStatus.HEALTHY: "ok",
        HealthStatus.DEGRADED: "degraded",
        HealthStatus.UNAVAILABLE: "error",
        HealthStatus.DISABLED: "error",
    }
    return mapping[status]
