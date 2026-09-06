"""Static module registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from energy_core.contracts.capabilities import DeviceCapability


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    module_id: str
    name: str
    version: str
    dependencies: tuple[str, ...] = ()
    capabilities_provided: tuple[DeviceCapability, ...] = ()
    capabilities_required: tuple[DeviceCapability, ...] = ()
    health_check: Callable[[], bool] | None = None
    configuration_schema: dict[str, Any] = field(default_factory=dict)


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleDescriptor] = {}

    def register(self, descriptor: ModuleDescriptor) -> None:
        if descriptor.module_id in self._modules:
            raise ValueError(f"Module already registered: {descriptor.module_id}")
        self._modules[descriptor.module_id] = descriptor

    def get(self, module_id: str) -> ModuleDescriptor | None:
        return self._modules.get(module_id)

    def list_modules(self) -> tuple[ModuleDescriptor, ...]:
        return tuple(self._modules.values())

    def clear(self) -> None:
        self._modules.clear()


default_module_registry = ModuleRegistry()
