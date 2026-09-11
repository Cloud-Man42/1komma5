"""Health reporting for packaged modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthLevel(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthStatus:
    level: HealthLevel
    message: str = ""
    details: dict[str, str] | None = None

    @classmethod
    def ok(cls, message: str = "ok") -> HealthStatus:
        return cls(level=HealthLevel.OK, message=message)

    @classmethod
    def unhealthy(cls, message: str) -> HealthStatus:
        return cls(level=HealthLevel.UNHEALTHY, message=message)
