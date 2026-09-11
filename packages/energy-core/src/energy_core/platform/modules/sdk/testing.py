"""Test harness helpers for module authors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from energy_core.platform.modules.sdk.context import EmicModuleContext


@dataclass(slots=True)
class FakeSite:
    site_id: str
    configuration: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FakeCapabilityRegistry:
    capabilities: set[str] = field(default_factory=set)

    def register(self, name: str) -> None:
        self.capabilities.add(name)

    def has(self, name: str) -> bool:
        return name in self.capabilities


@dataclass(slots=True)
class ModuleTestContext:
    site: FakeSite
    module_id: str
    version: str
    capability_registry: FakeCapabilityRegistry = field(default_factory=FakeCapabilityRegistry)

    def build_module_context(self, configuration: dict[str, Any] | None = None) -> EmicModuleContext:
        return EmicModuleContext(
            site_id=self.site.site_id,
            module_id=self.module_id,
            installed_version=self.version,
            configuration=configuration or {},
            services={"capabilities": self.capability_registry},
        )
