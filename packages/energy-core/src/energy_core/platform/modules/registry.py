"""Static module registry."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

from energy_core.platform.capabilities.types import Capability
from energy_core.platform.modules.packages.types import PackageSource
from energy_core.platform.modules.types import ModuleType


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    module_id: str
    name: str
    version: str
    module_type: ModuleType = ModuleType.FEATURE
    description: str = ""
    dependencies: tuple[str, ...] = ()
    capabilities_provided: tuple[Capability, ...] = ()
    capabilities_required: tuple[Capability, ...] = ()
    optional_capabilities: tuple[Capability, ...] = ()
    supports_per_site_activation: bool = True
    health_check: Callable[[], bool] | None = None
    configuration_schema: dict[str, Any] = field(default_factory=dict)
    onboardable: bool = False
    device_categories: tuple[str, ...] = ()
    connection_types: tuple[str, ...] = ()
    can_disable: bool = True
    onboard_handler: str | None = None
    supports_discovery: bool = False
    package_source: PackageSource = PackageSource.BUILT_IN
    installed_version: str | None = None
    publisher: str | None = None
    package_state: str | None = None
    removable: bool = False
    updatable: bool = False
    entrypoint: str | None = None


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleDescriptor] = {}

    def register(self, descriptor: ModuleDescriptor, *, allow_replace: bool = False) -> None:
        existing = self._modules.get(descriptor.module_id)
        if existing is not None and not allow_replace:
            raise ValueError(f"Module already registered: {descriptor.module_id}")
        if existing is not None and existing.package_source == PackageSource.BUILT_IN:
            raise ValueError(f"Cannot replace built-in module: {descriptor.module_id}")
        self._modules[descriptor.module_id] = descriptor

    def register_package_descriptor(self, descriptor: ModuleDescriptor) -> None:
        if descriptor.package_source != PackageSource.INSTALLED:
            raise ValueError("register_package_descriptor requires package_source=installed")
        self.register(descriptor, allow_replace=True)

    def enrich(self, module_id: str, **fields: Any) -> None:
        existing = self._modules.get(module_id)
        if existing is None:
            return
        self._modules[module_id] = replace(existing, **fields)

    def get(self, module_id: str) -> ModuleDescriptor | None:
        return self._modules.get(module_id)

    def list_modules(self) -> tuple[ModuleDescriptor, ...]:
        return tuple(self._modules.values())

    def clear(self) -> None:
        self._modules.clear()


default_module_registry = ModuleRegistry()
