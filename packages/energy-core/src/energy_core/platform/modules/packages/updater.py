"""Package update with backup, migration, and health gate."""

from __future__ import annotations

import shutil
from pathlib import Path

from packaging.version import Version
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.errors import (
    HEALTH_GATE_FAILED,
    MODULE_NOT_INSTALLED,
    VERSION_DOWNGRADE_NOT_ALLOWED,
    PackageError,
)
from energy_core.platform.modules.packages.extractor import PackageExtractor
from energy_core.platform.modules.packages.health_gate import evaluate_package_health
from energy_core.platform.modules.packages.impact import PackageImpactAnalyzer
from energy_core.platform.modules.packages.migration_runner import migrate_config, requires_migration
from energy_core.platform.modules.packages.package_lock import PackageMutationLock
from energy_core.platform.modules.packages.paths import ModulePackagePaths
from energy_core.platform.modules.packages.quarantine import quarantine_package
from energy_core.platform.modules.packages.rollback import PackageRollbackService
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import InstalledPackageRecord, PackageMutationResult, PackageState, SignatureStatus
from energy_core.platform.modules.packages.trust_read_model import build_install_metadata
from energy_core.platform.modules.packages.validator import PackageValidator


class PackageUpdater:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = InstalledPackageRepository(session)
        self._paths = ModulePackagePaths(settings.resolved_modules_path())
        self._extractor = PackageExtractor(self._paths)
        self._trust_store = PublisherTrustStore(session)
        self._validator = PackageValidator(settings, trust_store=self._trust_store)
        self._lock = PackageMutationLock(self._paths.root)

    async def update(
        self,
        module_id: str,
        archive_path: Path,
        *,
        allow_downgrade: bool = False,
    ) -> PackageMutationResult:
        current = await self._repo.get(module_id)
        if current is None:
            raise PackageError(f"module not installed: {module_id}", code=MODULE_NOT_INSTALLED)

        installed = {row.module_id: row.installed_version for row in await self._repo.list_all()}
        validation = await self._validator.validate_archive(
            archive_path,
            installed_versions={k: v for k, v in installed.items() if k != module_id},
            allow_reinstall=True,
        )
        if not validation.valid or validation.manifest is None or not validation.install_allowed:
            code = validation.errors[0] if validation.errors else "package_error"
            raise PackageError(code, code=code)

        manifest = validation.manifest
        if manifest.module_id != module_id:
            raise PackageError("module_id mismatch", code=MODULE_NOT_INSTALLED)

        if Version(manifest.version) < Version(current.installed_version) and not allow_downgrade:
            raise PackageError("version downgrade not allowed", code=VERSION_DOWNGRADE_NOT_ALLOWED)

        await PackageImpactAnalyzer(self._session, self._settings).assert_update_allowed(module_id, archive_path)

        if requires_migration(current.installed_version, manifest.version):
            staging_probe = self._paths.staging_dir(module_id, manifest.version)
            self._extractor.extract(archive_path, staging_probe)
            try:
                migrate_config(
                    staging_probe,
                    from_version=current.installed_version,
                    to_version=manifest.version,
                    configuration={},
                )
            except PackageError:
                shutil.rmtree(staging_probe, ignore_errors=True)
                raise
            shutil.rmtree(staging_probe, ignore_errors=True)

        with self._lock.acquire(module_id):
            backup_dir = self._paths.backup_dir(module_id, current.installed_version)
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(current.package_path, backup_dir)

            staging = self._paths.staging_dir(module_id, manifest.version)
            promoted = False
            try:
                self._extractor.extract(archive_path, staging)
                try:
                    evaluate_package_health(staging)
                except PackageError as exc:
                    if exc.code == HEALTH_GATE_FAILED:
                        shutil.rmtree(staging, ignore_errors=True)
                        raise
                installed_dir = self._paths.installed_dir(module_id, manifest.version)
                if installed_dir.exists():
                    shutil.rmtree(installed_dir)
                shutil.move(str(staging), str(installed_dir))
                promoted = True

                checksum = PackageValidator.compute_archive_checksum(archive_path)
                signature_status = SignatureStatus.VALID if validation.signature_valid else SignatureStatus.UNSIGNED
                updated = InstalledPackageRecord(
                    module_id=current.module_id,
                    installed_version=manifest.version,
                    package_state=PackageState.INSTALLED,
                    package_path=str(installed_dir),
                    staging_path=None,
                    publisher=manifest.publisher,
                    source=current.source,
                    checksum_sha256=checksum,
                    signature_status=signature_status,
                    rollback_version=current.installed_version,
                    previous_package_path=str(backup_dir),
                    module_api_version=manifest.module_api_version,
                    restart_required=True,
                    metadata=build_install_metadata(manifest, validation),
                )
                await self._repo.upsert(updated)
                await self._session.commit()
            except PackageError as exc:
                await self._session.rollback()
                if exc.code == HEALTH_GATE_FAILED and promoted:
                    try:
                        await PackageRollbackService(self._session, self._settings).rollback(module_id)
                    except PackageError:
                        await quarantine_package(
                            self._session,
                            current,
                            reason="health_gate_failed",
                            last_error=str(exc),
                        )
                shutil.rmtree(staging, ignore_errors=True)
                raise
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                try:
                    await PackageRollbackService(self._session, self._settings).rollback(module_id)
                except PackageError:
                    await quarantine_package(self._session, current, reason="update_failed")
                raise

        return PackageMutationResult(
            module_id=module_id,
            success=True,
            message="Package updated; restart required",
            package_state=PackageState.INSTALLED.value,
            installed_version=manifest.version,
            restart_required=True,
            rollback_version=current.installed_version,
        )
