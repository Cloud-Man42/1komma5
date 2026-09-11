"""Pre-flight impact analysis for package mutations."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.devices.registry import DeviceRegistry
from energy_core.platform.modules.packages.errors import CAPABILITY_REMOVAL_BLOCKED, PackageError
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import PackageImpactReport
from energy_core.platform.modules.packages.validator import PackageValidator
from energy_core.platform.modules.registry import default_module_registry


class PackageImpactAnalyzer:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = InstalledPackageRepository(session)
        self._trust_store = PublisherTrustStore(session)
        self._validator = PackageValidator(settings, trust_store=self._trust_store)
        self._devices = DeviceRegistry(session)

    async def analyze_install(self, archive_path: Path, *, module_id: str | None = None) -> PackageImpactReport:
        installed = {row.module_id: row.installed_version for row in await self._repo.list_all()}
        validation = await self._validator.validate_archive(
            archive_path,
            installed_versions=installed,
            allow_reinstall=module_id is not None,
        )
        if not validation.valid or validation.manifest is None:
            return PackageImpactReport(
                module_id=module_id or "unknown",
                warnings=validation.errors,
                restart_required=True,
            )

        manifest = validation.manifest
        capabilities_added = manifest.provided_capabilities
        capabilities_removed: tuple[str, ...] = ()
        affected_modules: tuple[str, ...] = ()
        warnings: list[str] = list(validation.warnings)

        existing = await self._repo.get(manifest.module_id)
        if existing is not None:
            descriptor = default_module_registry.get(manifest.module_id)
            old_caps = (
                tuple(c.value for c in descriptor.capabilities_provided)
                if descriptor is not None
                else ()
            )
            new_caps = set(manifest.provided_capabilities)
            capabilities_added = tuple(c for c in manifest.provided_capabilities if c not in old_caps)
            capabilities_removed = tuple(c for c in old_caps if c not in new_caps)
            if capabilities_removed:
                enabled_rows = await self._session.scalars(
                    select(SiteModuleConfigurationModel).where(
                        SiteModuleConfigurationModel.module_id == manifest.module_id,
                        SiteModuleConfigurationModel.enabled_override.is_(True),
                    )
                )
                if any(True for _ in enabled_rows):
                    warnings.append("update removes capabilities while module enabled on sites")

            for descriptor in default_module_registry.list_modules():
                if manifest.module_id in descriptor.dependencies:
                    affected_modules = (*affected_modules, descriptor.module_id)

        return PackageImpactReport(
            module_id=manifest.module_id,
            capabilities_added=capabilities_added,
            capabilities_removed=capabilities_removed,
            affected_modules=affected_modules,
            restart_required=True,
            warnings=tuple(warnings),
        )

    async def analyze_remove(self, module_id: str) -> PackageImpactReport:
        rows = await self._session.scalars(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.module_id == module_id,
                SiteModuleConfigurationModel.enabled_override.is_(True),
            )
        )
        enabled_sites = [str(row.site_id) for row in rows]
        dependents: list[str] = []
        for descriptor in default_module_registry.list_modules():
            if module_id in descriptor.dependencies:
                dependents.append(descriptor.module_id)

        device_records = await self._devices.list_referencing_module(module_id)
        device_ids = tuple(
            f"{record.device_id.device_type.value}:{record.device_id.id}" for record in device_records
        )
        site_ids = tuple(sorted({str(record.site_id) for record in device_records}))

        warnings: list[str] = []
        if enabled_sites:
            warnings.append("module enabled on one or more sites")
        if dependents:
            warnings.append("other modules depend on this module")
        if device_ids:
            warnings.append("registered devices reference this module")

        return PackageImpactReport(
            module_id=module_id,
            affected_modules=tuple(dependents),
            affected_sites=tuple(enabled_sites),
            affected_devices=device_ids,
            restart_required=True,
            warnings=tuple(warnings),
        )

    async def assert_update_allowed(self, module_id: str, archive_path: Path) -> PackageImpactReport:
        report = await self.analyze_install(archive_path, module_id=module_id)
        if report.capabilities_removed:
            enabled = await self._session.scalar(
                select(SiteModuleConfigurationModel.id)
                .where(
                    SiteModuleConfigurationModel.module_id == module_id,
                    SiteModuleConfigurationModel.enabled_override.is_(True),
                )
                .limit(1)
            )
            if enabled is not None:
                raise PackageError(
                    f"update removes capabilities: {', '.join(report.capabilities_removed)}",
                    code=CAPABILITY_REMOVAL_BLOCKED,
                )
        return report
