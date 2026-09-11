"""Rollback installed module packages."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.errors import MODULE_NOT_INSTALLED, ROLLBACK_UNAVAILABLE, PackageError
from energy_core.platform.modules.packages.paths import ModulePackagePaths
from energy_core.platform.modules.packages.types import PackageMutationResult, PackageState


class PackageRollbackService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = InstalledPackageRepository(session)
        self._paths = ModulePackagePaths(settings.resolved_modules_path())

    async def rollback(self, module_id: str) -> PackageMutationResult:
        current = await self._repo.get(module_id)
        if current is None:
            raise PackageError(f"module not installed: {module_id}", code=MODULE_NOT_INSTALLED)
        if not current.rollback_version or not current.previous_package_path:
            raise PackageError("rollback unavailable", code=ROLLBACK_UNAVAILABLE)

        backup_path = Path(current.previous_package_path)
        if not backup_path.exists():
            raise PackageError("rollback backup missing", code=ROLLBACK_UNAVAILABLE)

        target = self._paths.installed_dir(module_id, current.rollback_version)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(backup_path, target)

        restored = type(current)(
            module_id=current.module_id,
            installed_version=current.rollback_version,
            package_state=PackageState.INSTALLED,
            package_path=str(target),
            staging_path=None,
            publisher=current.publisher,
            source=current.source,
            checksum_sha256=current.checksum_sha256,
            signature_status=current.signature_status,
            rollback_version=None,
            previous_package_path=None,
            module_api_version=current.module_api_version,
            restart_required=True,
            metadata=current.metadata,
        )
        await self._repo.upsert(restored)
        await self._session.commit()

        return PackageMutationResult(
            module_id=module_id,
            success=True,
            message=f"Rolled back to {current.rollback_version}; restart required",
            package_state=PackageState.INSTALLED.value,
            installed_version=current.rollback_version,
            restart_required=True,
        )
