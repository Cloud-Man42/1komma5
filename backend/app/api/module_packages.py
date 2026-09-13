"""Module package admin API."""

from __future__ import annotations

import tempfile
from pathlib import Path
from dataclasses import asdict
from typing import Any

from app.admin_audit_helpers import audit_admin_mutation
from app.user_auth import require_permission
from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.packages.errors import PackageError
from energy_core.platform.modules.packages.impact import PackageImpactAnalyzer
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.remover import PackageRemover
from energy_core.platform.modules.packages.rollback import PackageRollbackService
from energy_core.platform.modules.packages.updater import PackageUpdater
from energy_core.platform.modules.packages.catalog import resolve_catalog_package
from energy_core.platform.modules.packages.store_service import PackageStoreService
from energy_core.platform.modules.packages.trust_read_model import logical_package_id
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore
from energy_core.platform.modules.packages.types import ModuleManifest
from energy_core.platform.modules.packages.validator import PackageValidator
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/packages", tags=["module-packages"])


class PackageListItem(BaseModel):
    module_id: str
    installed_version: str
    package_state: str
    publisher: str
    source: str
    checksum_sha256: str
    signature_status: str
    rollback_version: str | None = None
    restart_required: bool = False
    module_api_version: int = 1


class PackageDetailResponse(PackageListItem):
    logical_package_id: str
    publisher_status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PackageMutationResponse(BaseModel):
    module_id: str
    success: bool
    message: str
    package_state: str
    installed_version: str | None = None
    restart_required: bool = False
    rollback_version: str | None = None


class ValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    manifest: dict[str, Any] | None = None
    signed: bool = False
    signature_valid: bool = False
    publisher_trusted: bool = False
    publisher_identity_valid: bool = False
    install_allowed: bool = False
    policy_decision: str | None = None
    policy_reason_codes: list[str] = Field(default_factory=list)
    policy_explanation: str | None = None
    publisher_tier: str | None = None
    control_capable: bool = False
    policy_version: int | None = None
    permissions: list[str] = Field(default_factory=list)
    provided_capabilities: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    optional_capabilities: list[str] = Field(default_factory=list)
    module_dependencies: list[dict[str, str]] = Field(default_factory=list)
    minimum_emic_version: str | None = None
    maximum_emic_version: str | None = None
    module_api_version: int | None = None
    compatible_with_emic: bool | None = None


class ImpactResponse(BaseModel):
    module_id: str
    affected_modules: list[str] = Field(default_factory=list)
    affected_sites: list[str] = Field(default_factory=list)
    affected_devices: list[str] = Field(default_factory=list)
    capabilities_added: list[str] = Field(default_factory=list)
    capabilities_removed: list[str] = Field(default_factory=list)
    restart_required: bool = False
    warnings: list[str] = Field(default_factory=list)


class StorePackageCardResponse(BaseModel):
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
    rollback_version: str | None = None
    restart_required: bool = False
    checksum_sha256: str
    runtime_checksum: str | None = None
    enabled_sites: list[str] = Field(default_factory=list)
    runtime_status: str | None = None
    runtime_version: str | None = None
    version_match: bool | None = None
    checksum_match: bool | None = None
    needs_attention: bool = False
    attention_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogEntryResponse(BaseModel):
    entry_id: str
    module_id: str
    name: str
    version: str
    publisher: str
    description: str
    package_filename: str
    trusted: bool = True


class StoreOverviewResponse(BaseModel):
    installed: list[StorePackageCardResponse] = Field(default_factory=list)
    catalog: list[CatalogEntryResponse] = Field(default_factory=list)
    needs_attention: list[StorePackageCardResponse] = Field(default_factory=list)
    allow_unsigned_modules: bool = False


class PackageSiteActivationResponse(BaseModel):
    site_slug: str
    site_name: str
    enabled: bool
    runtime_status: str | None = None
    runtime_version: str | None = None


def _manifest_summary(manifest: ModuleManifest | None) -> dict[str, Any] | None:
    if manifest is None:
        return None
    return {
        "module_id": manifest.module_id,
        "name": manifest.name,
        "version": manifest.version,
        "publisher": manifest.publisher,
        "module_type": manifest.module_type,
        "description": manifest.description,
    }


def _validation_payload(result, manifest: ModuleManifest | None) -> dict[str, Any]:
    summary = _manifest_summary(manifest)
    return {
        "valid": result.valid,
        "errors": list(result.errors),
        "warnings": list(result.warnings),
        "manifest": summary,
        "signed": result.signed,
        "signature_valid": result.signature_valid,
        "publisher_trusted": result.publisher_trusted,
        "publisher_identity_valid": result.publisher_identity_valid,
        "install_allowed": result.install_allowed,
        "policy_decision": result.policy_decision,
        "policy_reason_codes": list(result.policy_reason_codes),
        "policy_explanation": result.policy_explanation,
        "publisher_tier": result.publisher_tier,
        "control_capable": result.control_capable,
        "policy_version": result.policy_version,
        "permissions": list(manifest.permissions) if manifest else [],
        "provided_capabilities": list(manifest.provided_capabilities) if manifest else [],
        "required_capabilities": list(manifest.required_capabilities) if manifest else [],
        "optional_capabilities": list(manifest.optional_capabilities) if manifest else [],
        "module_dependencies": [
            {"module_id": dep.module_id, "version_range": dep.version_range}
            for dep in (manifest.module_dependencies if manifest else ())
        ],
        "minimum_emic_version": manifest.minimum_emic_version if manifest else None,
        "maximum_emic_version": manifest.maximum_emic_version if manifest else None,
        "module_api_version": manifest.module_api_version if manifest else None,
        "compatible_with_emic": result.valid or not result.errors,
    }


def _package_error(exc: PackageError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.code, "message": str(exc)})


async def _save_upload(upload: UploadFile) -> Path:
    suffix = ".emicpkg"
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    path = Path(handle.name)
    handle.close()
    content = await upload.read()
    path.write_bytes(content)
    return path


def _card_response(card) -> StorePackageCardResponse:
    return StorePackageCardResponse(
        module_id=card.module_id,
        name=card.name,
        installed_version=card.installed_version,
        publisher=card.publisher,
        package_state=card.package_state,
        signature_status=card.signature_status,
        signed=card.signed,
        signature_valid=card.signature_valid,
        publisher_trusted=card.publisher_trusted,
        publisher_status=card.publisher_status,
        install_allowed=card.install_allowed,
        rollback_version=card.rollback_version,
        restart_required=card.restart_required,
        checksum_sha256=card.checksum_sha256,
        runtime_checksum=card.runtime_checksum,
        enabled_sites=list(card.enabled_sites),
        runtime_status=card.runtime_status,
        runtime_version=card.runtime_version,
        version_match=card.version_match,
        checksum_match=card.checksum_match,
        needs_attention=card.needs_attention,
        attention_reasons=list(card.attention_reasons),
        metadata=card.metadata,
    )


@router.get("", response_model=list[PackageListItem])
async def list_installed_packages(
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("modules.manage")),
) -> list[PackageListItem]:
    repo = InstalledPackageRepository(session)
    return [
        PackageListItem(
            module_id=row.module_id,
            installed_version=row.installed_version,
            package_state=row.package_state.value,
            publisher=row.publisher,
            source=row.source,
            checksum_sha256=row.checksum_sha256,
            signature_status=row.signature_status.value,
            rollback_version=row.rollback_version,
            restart_required=row.restart_required,
            module_api_version=row.module_api_version,
        )
        for row in await repo.list_all()
    ]


@router.get("/store/overview", response_model=StoreOverviewResponse)
async def store_overview(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> StoreOverviewResponse:
    overview = await PackageStoreService(session, settings).build_overview()

    return StoreOverviewResponse(
        installed=[_card_response(card) for card in overview.installed],
        catalog=[
            CatalogEntryResponse(
                entry_id=entry.entry_id,
                module_id=entry.module_id,
                name=entry.name,
                version=entry.version,
                publisher=entry.publisher,
                description=entry.description,
                package_filename=entry.package_filename,
                trusted=entry.trusted,
            )
            for entry in overview.catalog
        ],
        needs_attention=[_card_response(card) for card in overview.needs_attention],
        allow_unsigned_modules=overview.allow_unsigned_modules,
    )


@router.get("/store/packages/{module_id}", response_model=StorePackageCardResponse)
async def store_package_detail(
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> StorePackageCardResponse:
    card = await PackageStoreService(session, settings).get_package_card(module_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return _card_response(card)


@router.get("/{module_id}/sites", response_model=list[PackageSiteActivationResponse])
async def package_site_activations(
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> list[PackageSiteActivationResponse]:
    activations = await PackageStoreService(session, settings).site_activations(module_id)
    return [
        PackageSiteActivationResponse(
            site_slug=item.site_slug,
            site_name=item.site_name,
            enabled=item.enabled,
            runtime_status=item.runtime_status,
            runtime_version=item.runtime_version,
        )
        for item in activations
    ]


@router.post("/catalog/{entry_id}/validate", response_model=ValidationResponse)
async def validate_catalog_entry(
    entry_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ValidationResponse:
    archive = resolve_catalog_package(settings, entry_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    installed = {row.module_id: row.installed_version for row in await InstalledPackageRepository(session).list_all()}
    trust_store = PublisherTrustStore(session)
    result = await PackageValidator(settings, trust_store=trust_store, session=session).validate_archive(archive, installed_versions=installed)
    return ValidationResponse(**_validation_payload(result, result.manifest))


@router.post("/catalog/{entry_id}/impact", response_model=ImpactResponse)
async def catalog_entry_impact(
    entry_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ImpactResponse:
    archive = resolve_catalog_package(settings, entry_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    report = await PackageImpactAnalyzer(session, settings).analyze_install(archive)
    return ImpactResponse(
        module_id=report.module_id,
        affected_modules=list(report.affected_modules),
        affected_sites=list(report.affected_sites),
        affected_devices=list(report.affected_devices),
        capabilities_added=list(report.capabilities_added),
        capabilities_removed=list(report.capabilities_removed),
        restart_required=report.restart_required,
        warnings=list(report.warnings),
    )


@router.post("/catalog/{entry_id}/install", response_model=PackageMutationResponse)
async def install_catalog_entry(
    entry_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageMutationResponse:
    archive = resolve_catalog_package(settings, entry_id)
    if archive is None:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    try:
        result = await PackageInstaller(session, settings).install(archive, source="catalog")
        await audit_admin_mutation(
            request,
            session,
            action="module.installed",
            resource_type="module_package",
            resource_id=result.module_id,
            summary={"version": result.installed_version, "source": "catalog", "entry_id": entry_id},
        )
        return PackageMutationResponse(**asdict(result))
    except PackageError as exc:
        raise _package_error(exc) from exc


@router.get("/{module_id}", response_model=PackageDetailResponse)
async def get_installed_package(
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageDetailResponse:
    repo = InstalledPackageRepository(session)
    row = await repo.get(module_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    from energy_core.platform.modules.packages.trust_read_model import trust_view_from_record

    trust = trust_view_from_record(row)
    return PackageDetailResponse(
        module_id=row.module_id,
        installed_version=row.installed_version,
        package_state=row.package_state.value,
        publisher=row.publisher,
        source=row.source,
        checksum_sha256=row.checksum_sha256,
        signature_status=row.signature_status.value,
        rollback_version=row.rollback_version,
        restart_required=row.restart_required,
        module_api_version=row.module_api_version,
        logical_package_id=logical_package_id(row.module_id, row.installed_version),
        publisher_status=trust["publisher_status"],
        metadata=row.metadata,
    )


@router.post("/validate", response_model=ValidationResponse)
async def validate_package(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    upload: UploadFile = File(...),
    _: None = Depends(require_permission("modules.manage")),
) -> ValidationResponse:
    path = await _save_upload(upload)
    try:
        installed = {row.module_id: row.installed_version for row in await InstalledPackageRepository(session).list_all()}
        trust_store = PublisherTrustStore(session)
        result = await PackageValidator(settings, trust_store=trust_store, session=session).validate_archive(path, installed_versions=installed)
        payload = _validation_payload(result, result.manifest)
        await audit_admin_mutation(
            request,
            session,
            action="package.validated",
            resource_type="module_package",
            resource_id=payload["manifest"].get("module_id") if payload["manifest"] else None,
            summary={"valid": result.valid, "errors": list(result.errors)},
        )
        await session.commit()
        return ValidationResponse(**payload)
    finally:
        path.unlink(missing_ok=True)


@router.post("/install", response_model=PackageMutationResponse)
async def install_package(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    upload: UploadFile = File(...),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageMutationResponse:
    path = await _save_upload(upload)
    try:
        result = await PackageInstaller(session, settings).install(path)
        await audit_admin_mutation(
            request,
            session,
            action="module.installed",
            resource_type="module_package",
            resource_id=result.module_id,
            summary={"version": result.installed_version},
        )
        return PackageMutationResponse(**asdict(result))
    except PackageError as exc:
        raise _package_error(exc) from exc
    finally:
        path.unlink(missing_ok=True)


@router.post("/{module_id}/update", response_model=PackageMutationResponse)
async def update_package(
    module_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    upload: UploadFile = File(...),
    allow_downgrade: bool = Query(default=False),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageMutationResponse:
    path = await _save_upload(upload)
    try:
        result = await PackageUpdater(session, settings).update(module_id, path, allow_downgrade=allow_downgrade)
        await audit_admin_mutation(
            request,
            session,
            action="module.updated",
            resource_type="module_package",
            resource_id=module_id,
            summary={"version": result.installed_version, "rollback_version": result.rollback_version},
        )
        return PackageMutationResponse(**asdict(result))
    except PackageError as exc:
        raise _package_error(exc) from exc
    finally:
        path.unlink(missing_ok=True)


@router.post("/{module_id}/rollback", response_model=PackageMutationResponse)
async def rollback_package(
    module_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageMutationResponse:
    try:
        result = await PackageRollbackService(session, settings).rollback(module_id)
        await audit_admin_mutation(
            request,
            session,
            action="module.rollback",
            resource_type="module_package",
            resource_id=module_id,
            summary={"version": result.installed_version},
        )
        return PackageMutationResponse(**asdict(result))
    except PackageError as exc:
        raise _package_error(exc) from exc


@router.delete("/{module_id}", response_model=PackageMutationResponse)
async def remove_package(
    module_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> PackageMutationResponse:
    try:
        result = await PackageRemover(session, settings).remove(module_id)
        await audit_admin_mutation(
            request,
            session,
            action="module.removed",
            resource_type="module_package",
            resource_id=module_id,
        )
        return PackageMutationResponse(**asdict(result))
    except PackageError as exc:
        raise _package_error(exc) from exc


@router.post("/{module_id}/impact", response_model=ImpactResponse)
async def analyze_package_impact(
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    upload: UploadFile | None = File(default=None),
    _: None = Depends(require_permission("modules.manage")),
) -> ImpactResponse:
    analyzer = PackageImpactAnalyzer(session, settings)
    if upload is not None:
        path = await _save_upload(upload)
        try:
            report = await analyzer.analyze_install(path, module_id=module_id)
        finally:
            path.unlink(missing_ok=True)
    else:
        report = await analyzer.analyze_remove(module_id)
    return ImpactResponse(
        module_id=report.module_id,
        affected_modules=list(report.affected_modules),
        affected_sites=list(report.affected_sites),
        affected_devices=list(report.affected_devices),
        capabilities_added=list(report.capabilities_added),
        capabilities_removed=list(report.capabilities_removed),
        restart_required=report.restart_required,
        warnings=list(report.warnings),
    )
