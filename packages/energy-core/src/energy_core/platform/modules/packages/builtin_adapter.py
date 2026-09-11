"""Built-in module metadata adapter."""

from __future__ import annotations

from energy_core.platform.modules.packages.paths import BUILTIN_MODULE_IDS
from energy_core.platform.modules.packages.types import PackageSource
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry


class BuiltInModuleAdapter:
    @staticmethod
    def enrich_registry() -> None:
        for descriptor in default_module_registry.list_modules():
            if descriptor.module_id not in BUILTIN_MODULE_IDS:
                continue
            default_module_registry.enrich(
                descriptor.module_id,
                package_source=PackageSource.BUILT_IN,
                removable=False,
                updatable=False,
                installed_version=descriptor.version,
            )

    @staticmethod
    def is_builtin(module_id: str) -> bool:
        return module_id in BUILTIN_MODULE_IDS
