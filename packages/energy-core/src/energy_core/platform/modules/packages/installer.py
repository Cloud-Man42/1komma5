"""Staged install transaction for module packages."""

from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.errors import PackageError, SIGNATURE_INVALID
from energy_core.platform.modules.packages.extractor import PackageExtractor
from energy_core.platform.modules.packages.package_lock import PackageMutationLock
from energy_core.platform.modules.packages.paths import ModulePackagePaths
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import (
    InstalledPackageRecord,
    PackageMutationResult,
    PackageState,
    SignatureStatus,
)
from energy_core.platform.modules.packages.trust_read_model import build_install_metadata
from energy_core.platform.modules.packages.validator import PackageValidator


class PackageInstaller:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._paths = ModulePackagePaths(settings.resolved_modules_path())
        self._paths.ensure_layout()
        self._repo = InstalledPackageRepository(session)
        self._trust_store = PublisherTrustStore(session)
        self._validator = PackageValidator(settings, trust_store=self._trust_store)
        self._extractor = PackageExtractor(self._paths)
        self._lock = PackageMutationLock(self._paths.root)

    async def install(self, archive_path: Path, *, source: str = "upload") -> PackageMutationResult:
        installed = {row.module_id: row.installed_version for row in await self._repo.list_all()}
        validation = await self._validator.validate_archive(archive_path, installed_versions=installed)
        if not validation.valid or validation.manifest is None or not validation.install_allowed:
            code = validation.errors[0] if validation.errors else "package_error"
            raise PackageError(code, code=code)

        manifest = validation.manifest
        with self._lock.acquire(manifest.module_id):
            staging = self._paths.staging_dir(manifest.module_id, manifest.version)
            try:
                self._extractor.extract(archive_path, staging)
                signature_status = SignatureStatus.VALID if validation.signature_valid else SignatureStatus.UNSIGNED
                if signature_status == SignatureStatus.UNSIGNED and not self._settings.emic_allow_unsigned_modules:
                    raise PackageError("unsigned package rejected", code=SIGNATURE_INVALID)

                installed_dir = self._paths.installed_dir(manifest.module_id, manifest.version)
                if installed_dir.exists():
                    shutil.rmtree(installed_dir)
                shutil.move(str(staging), str(installed_dir))

                checksum = PackageValidator.compute_archive_checksum(archive_path)
                record = InstalledPackageRecord(
                    module_id=manifest.module_id,
                    installed_version=manifest.version,
                    package_state=PackageState.INSTALLED,
                    package_path=str(installed_dir),
                    publisher=manifest.publisher,
                    source=source,
                    checksum_sha256=checksum,
                    signature_status=signature_status,
                    rollback_version=None,
                    previous_package_path=None,
                    module_api_version=manifest.module_api_version,
                    restart_required=True,
                    metadata=build_install_metadata(manifest, validation),
                )
                await self._repo.upsert(record)
                await self._session.commit()
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise

        return PackageMutationResult(
            module_id=manifest.module_id,
            success=True,
            message="Package installed; restart required for activation",
            package_state=PackageState.INSTALLED.value,
            installed_version=manifest.version,
            restart_required=True,
        )
