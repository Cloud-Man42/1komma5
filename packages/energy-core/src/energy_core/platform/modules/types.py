"""Module platform enums."""

from __future__ import annotations

from enum import StrEnum


class ModuleType(StrEnum):
    CORE = "core"
    FEATURE = "feature"
    INTEGRATION = "integration"
    PROVIDER = "provider"


class ActivationStatus(StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class RuntimeStatus(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ModuleHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
