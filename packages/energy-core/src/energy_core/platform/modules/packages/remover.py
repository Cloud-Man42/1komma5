"""Remove installed module packages."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.modules.packages.errors import (
    MODULE_HAS_DEVICES,
    MODULE_IN_USE,
    MODULE_NOT_INSTALLED,
    PackageError,
)
from energy_core.platform.modules.packages.impact import PackageImpactAnalyzer
from energy_core.platform.modules.packages.package_lock import PackageMutationLock
from energy_core.platform.modules.packages.paths import ModulePackagePaths
from energy_core.platform.modules.packages.types import PackageMutationResult, PackageState


class PackageRemover:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = InstalledPackageRepository(session)
        self._impact = PackageImpactAnalyzer(session, settings)
        self._paths = ModulePackagePaths(settings.resolved_modules_path())
        self._lock = PackageMutationLock(self._paths.root)

    async def remove(self, module_id: str) -> PackageMutationResult:
        current = await self._repo.get(module_id)
        if current is None:
            raise PackageError(f"module not installed: {module_id}", code=MODULE_NOT_INSTALLED)

        impact = await self._impact.analyze_remove(module_id)
        if impact.affected_devices:
            raise PackageError(
                "module has registered devices",
                code=MODULE_HAS_DEVICES,
            )
        if impact.affected_sites or impact.affected_modules:
            raise PackageError("module in use", code=MODULE_IN_USE)

        with self._lock.acquire(module_id):
            package_path = Path(current.package_path)
            if package_path.exists():
                shutil.rmtree(package_path, ignore_errors=True)

            await self._repo.delete(module_id)
            await self._session.commit()

        return PackageMutationResult(
            module_id=module_id,
            success=True,
            message="Package removed; restart required",
            package_state=PackageState.REMOVING.value,
            restart_required=True,
        )

    async def is_enabled_anywhere(self, module_id: str) -> bool:
        row = await self._session.scalar(
            select(SiteModuleConfigurationModel.id)
            .where(
                SiteModuleConfigurationModel.module_id == module_id,
                SiteModuleConfigurationModel.enabled_override.is_(True),
            )
            .limit(1)
        )
        return row is not None
