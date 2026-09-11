"""Module Store read models and aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.cache.module_runtime_state import read_runtime_states
from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models import SiteModel
from energy_core.db.models.modules import SiteModuleConfigurationModel
from energy_core.platform.modules.packages.catalog import CatalogEntry, list_catalog_entries
from energy_core.platform.modules.packages.trust_read_model import trust_view_from_record
from energy_core.platform.modules.packages.types import PackageState
from energy_core.platform.modules.registry import default_module_registry


@dataclass(frozen=True, slots=True)
class PackageSiteActivation:
    site_slug: str
    site_name: str
    enabled: bool
    runtime_status: str | None = None
    runtime_version: str | None = None


@dataclass(frozen=True, slots=True)
class StorePackageCard:
    module_id: str
    name: str
    installed_version: str
    publisher: str
    package_state: str
    signature_status: str
    signed: bool
    signature_valid: bool
    publisher_trusted: bool
    publisher_status: str
    install_allowed: bool
    rollback_version: str | None
    restart_required: bool
    checksum_sha256: str
    runtime_checksum: str | None
    enabled_sites: tuple[str, ...]
    runtime_status: str | None
    runtime_version: str | None
    version_match: bool | None
    checksum_match: bool | None
    needs_attention: bool
    attention_reasons: tuple[str, ...]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class StoreOverview:
    installed: tuple[StorePackageCard, ...]
    catalog: tuple[CatalogEntry, ...]
    needs_attention: tuple[StorePackageCard, ...]
    allow_unsigned_modules: bool


class PackageStoreService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repo = InstalledPackageRepository(session)

    def _card_from_record(self, row, *, enabled_by_module: dict[str, list[str]], runtime_by_module: dict[str, dict[str, Any]]) -> StorePackageCard:
        descriptor = default_module_registry.get(row.module_id)
        name = str(row.metadata.get("name") or (descriptor.name if descriptor else row.module_id))
        trust = trust_view_from_record(row)
        attention: list[str] = []
        if row.package_state == PackageState.QUARANTINED:
            attention.append("quarantined")
        if row.package_state == PackageState.BROKEN:
            attention.append("broken")
        if row.restart_required:
            attention.append("restart_required")
        if row.metadata.get("quarantine_reason"):
            attention.append(str(row.metadata["quarantine_reason"]))
        runtime = runtime_by_module.get(row.module_id)
        runtime_version = runtime.get("version") if runtime else None
        runtime_checksum = runtime.get("checksum") if runtime else None
        version_match = None
        checksum_match = None
        if runtime_version is not None:
            version_match = runtime_version == row.installed_version
            if version_match is False:
                attention.append("version_mismatch")
        if runtime_checksum is not None:
            checksum_match = runtime_checksum.lower() == row.checksum_sha256.lower()
            if checksum_match is False:
                attention.append("checksum_mismatch")
        return StorePackageCard(
            module_id=row.module_id,
            name=name,
            installed_version=row.installed_version,
            publisher=row.publisher,
            package_state=row.package_state.value,
            signature_status=row.signature_status.value,
            signed=trust["signed"],
            signature_valid=trust["signature_valid"],
            publisher_trusted=trust["publisher_trusted"],
            publisher_status=trust["publisher_status"],
            install_allowed=trust["install_allowed"],
            rollback_version=row.rollback_version,
            restart_required=row.restart_required,
            checksum_sha256=row.checksum_sha256,
            runtime_checksum=runtime_checksum,
            enabled_sites=tuple(enabled_by_module.get(row.module_id, [])),
            runtime_status=runtime.get("status") if runtime else None,
            runtime_version=runtime_version,
            version_match=version_match,
            checksum_match=checksum_match,
            needs_attention=bool(attention),
            attention_reasons=tuple(attention),
            metadata=dict(row.metadata),
        )

    async def _runtime_by_module(self) -> tuple[dict[str, list[str]], dict[str, dict[str, Any]]]:
        sites = (await self._session.scalars(select(SiteModel))).all()
        enabled_by_module: dict[str, list[str]] = {}
        runtime_by_module: dict[str, dict[str, Any]] = {}
        for site in sites:
            rows = await self._session.scalars(
                select(SiteModuleConfigurationModel).where(
                    SiteModuleConfigurationModel.site_id == site.id,
                    SiteModuleConfigurationModel.enabled_override.is_(True),
                )
            )
            for row in rows:
                enabled_by_module.setdefault(row.module_id, []).append(site.slug)
            distributed = await read_runtime_states(self._settings, site.id)
            for module_id, snapshot in distributed.items():
                if not snapshot.module_version and not snapshot.package_checksum:
                    continue
                current = runtime_by_module.get(module_id)
                if current is None or snapshot.runtime_state.value == "running":
                    runtime_by_module[module_id] = {
                        "status": snapshot.runtime_state.value,
                        "version": snapshot.module_version,
                        "checksum": snapshot.package_checksum,
                    }
        return enabled_by_module, runtime_by_module

    async def build_overview(self) -> StoreOverview:
        installed_rows = await self._repo.list_all()
        enabled_by_module, runtime_by_module = await self._runtime_by_module()
        cards = [
            self._card_from_record(row, enabled_by_module=enabled_by_module, runtime_by_module=runtime_by_module)
            for row in installed_rows
        ]
        needs_attention = tuple(card for card in cards if card.needs_attention)
        catalog = list_catalog_entries(self._settings)
        return StoreOverview(
            installed=tuple(cards),
            catalog=catalog,
            needs_attention=needs_attention,
            allow_unsigned_modules=self._settings.emic_allow_unsigned_modules,
        )

    async def get_package_card(self, module_id: str) -> StorePackageCard | None:
        row = await self._repo.get(module_id)
        if row is None:
            return None
        enabled_by_module, runtime_by_module = await self._runtime_by_module()
        return self._card_from_record(row, enabled_by_module=enabled_by_module, runtime_by_module=runtime_by_module)

    async def site_activations(self, module_id: str) -> tuple[PackageSiteActivation, ...]:
        sites = (await self._session.scalars(select(SiteModel))).all()
        activations: list[PackageSiteActivation] = []
        for site in sites:
            row = await self._session.scalar(
                select(SiteModuleConfigurationModel).where(
                    SiteModuleConfigurationModel.site_id == site.id,
                    SiteModuleConfigurationModel.module_id == module_id,
                )
            )
            enabled = bool(row.enabled_override) if row and row.enabled_override is not None else False
            distributed = await read_runtime_states(self._settings, site.id)
            snapshot = distributed.get(module_id)
            activations.append(
                PackageSiteActivation(
                    site_slug=site.slug,
                    site_name=site.name,
                    enabled=enabled,
                    runtime_status=snapshot.runtime_state.value if snapshot else None,
                    runtime_version=snapshot.module_version if snapshot else None,
                )
            )
        return tuple(activations)
