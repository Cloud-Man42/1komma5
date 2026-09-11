"""Normalized onboarding DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RestartRequired(StrEnum):
    NONE = "none"
    MODULE = "module"
    INTEGRATION = "integration"


@dataclass(frozen=True, slots=True)
class CapabilityProbe:
    name: str
    kind: str
    available: bool


@dataclass(frozen=True, slots=True)
class DiscoveryDevice:
    external_id: str
    name: str
    device_type: str
    manufacturer: str = ""
    model: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConnectionTestResult:
    success: bool
    message: str
    devices_found: tuple[DiscoveryDevice, ...] = ()
    capabilities: tuple[CapabilityProbe, ...] = ()
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    supported: bool
    devices: tuple[DiscoveryDevice, ...] = ()
    message: str = ""
