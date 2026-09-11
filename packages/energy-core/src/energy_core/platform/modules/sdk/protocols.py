"""SDK runtime protocols."""

from __future__ import annotations

from typing import Any, Protocol

from energy_core.platform.modules.sdk.context import EmicModuleContext
from energy_core.platform.modules.sdk.health import HealthStatus


class EmicModuleRuntime(Protocol):
    def start(self, ctx: EmicModuleContext) -> None: ...

    def stop(self, ctx: EmicModuleContext) -> None: ...

    def health(self) -> HealthStatus: ...


class EmicModule(Protocol):
    def create_module(self, context: EmicModuleContext) -> EmicModuleRuntime: ...


class ModuleConfigurationHandler(Protocol):
    def migrate_configuration(
        self,
        *,
        from_version: str,
        to_version: str,
        configuration: dict[str, Any],
    ) -> dict[str, Any]: ...
