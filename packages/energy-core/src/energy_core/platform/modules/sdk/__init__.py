"""EMIC Module SDK — contracts for packaged modules."""

from energy_core.platform.modules.sdk.context import EmicModuleContext
from energy_core.platform.modules.sdk.health import HealthStatus
from energy_core.platform.modules.sdk.manifest import parse_manifest_dict
from energy_core.platform.modules.sdk.migration import ModuleMigration
from energy_core.platform.modules.sdk.protocols import (
    EmicModule,
    EmicModuleRuntime,
    ModuleConfigurationHandler,
)
from energy_core.platform.modules.sdk.testing import ModuleTestContext

__all__ = [
    "EmicModule",
    "EmicModuleContext",
    "EmicModuleRuntime",
    "HealthStatus",
    "ModuleConfigurationHandler",
    "ModuleMigration",
    "ModuleTestContext",
    "parse_manifest_dict",
]
