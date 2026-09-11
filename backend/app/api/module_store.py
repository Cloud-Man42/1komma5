"""Unified Module Store admin API (Sprint D)."""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.platform.modules.distribution.artifact_repository import ArtifactRepository
from energy_core.platform.modules.distribution.staging_service import ArtifactStagingService
from energy_core.platform.modules.distribution.types import ArtifactState, DistributionError
from energy_core.platform.modules.packages.catalog import resolve_catalog_package
from energy_core.platform.modules.packages.errors import PackageError
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.paths import is_protected_module_id
from energy_core.platform.modules.store.catalog_service import StoreCatalogService
from energy_core.platform.modules.store.types import StorePrimaryAction
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/store", tags=["module-store"])

_MODULE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


def _validate_module_id(module_id: str) -> str:
    if ".." in module_id or "/" in module_id or "\\" in module_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid module_id")
    if not _MODULE_ID_RE.match(module_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid module_id format")
    return module_id


def _serialize(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, tuple):
        return [_serialize(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


class PreflightRequest(BaseModel):
    site_slug: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class InstallRequest(BaseModel):
    site_slug: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    source: str = "auto"


class InstallResponse(BaseModel):
    success: bool
    message: str
    module_id: str
    version: str
    package_state: str | None = None
    artifact_id: int | None = None
    reason_codes: list[str] = Field(default_factory=list)


@router.get("/status")
async def store_status(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    service = StoreCatalogService(session, settings)
    return _serialize(await service.build_status())


@router.get("")
async def list_store_modules(
    request: Request,
    search: str | None = Query(None, max_length=200),
    category: str | None = None,
    trust: str | None = None,
    security: str | None = None,
    installed: bool | None = None,
    update_available: bool | None = None,
    compatible: bool | None = None,
    control_capable: bool | None = None,
    official: bool | None = Query(None, alias="official"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    sort: str = Query("recommended"),
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    service = StoreCatalogService(session, settings)
    result = await service.list_catalog(
        search=search,
        category=category,
        trust=trust,
        security=security,
        installed=installed,
        update_available=update_available,
        compatible=compatible,
        control_capable=control_capable,
        official_only=official,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return _serialize(result)


@router.get("/security")
async def store_security_center(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    service = StoreCatalogService(session, settings)
    return _serialize(await service.build_security_center())


@router.get("/publishers")
async def list_store_publishers(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[dict[str, Any]]:
    service = StoreCatalogService(session, settings)
    return [_serialize(p) for p in await service.list_publishers()]


@router.get("/publishers/{publisher_id}")
async def get_store_publisher(
    publisher_id: str,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    service = StoreCatalogService(session, settings)
    detail = await service.get_publisher(publisher_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publisher not found")
    return _serialize(detail)


@router.get("/{module_id}")
async def get_store_module(
    module_id: str,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    module_id = _validate_module_id(module_id)
    service = StoreCatalogService(session, settings)
    detail = await service.get_module_detail(module_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if hash(module_id) % 10 == 0:
        await audit_admin_mutation(
            request,
            session,
            action="store.module_viewed",
            resource_type="module_store",
            resource_id=module_id,
        )
    return _serialize(detail)


@router.get("/{module_id}/releases")
async def list_store_releases(
    module_id: str,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> list[dict[str, Any]]:
    module_id = _validate_module_id(module_id)
    service = StoreCatalogService(session, settings)
    releases = await service.list_releases(module_id)
    if not releases:
        detail = await service.get_module_detail(module_id)
        if detail is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return [_serialize(r) for r in releases]


@router.post("/{module_id}/{version}/preflight")
async def store_preflight(
    module_id: str,
    version: str,
    body: PreflightRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    module_id = _validate_module_id(module_id)
    service = StoreCatalogService(session, settings)
    result = await service.preflight(
        module_id,
        version,
        site_slug=body.site_slug,
        config=body.config,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module or version not found")
    await audit_admin_mutation(
        request,
        session,
        action="store.preflight_requested",
        resource_type="module_store",
        resource_id=f"{module_id}@{version}",
    )
    return _serialize(result)


@router.post("/{module_id}/{version}/install")
async def store_install(
    module_id: str,
    version: str,
    body: InstallRequest,
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> InstallResponse:
    module_id = _validate_module_id(module_id)
    if is_protected_module_id(module_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Protected module namespace")

    service = StoreCatalogService(session, settings)
    preflight = await service.preflight(module_id, version, site_slug=body.site_slug, config=body.config)
    if preflight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module or version not found")
    if not preflight.install_allowed and not preflight.stage_allowed:
        await audit_admin_mutation(
            request,
            session,
            action="store.install_blocked",
            resource_type="module_store",
            resource_id=f"{module_id}@{version}",
            summary={"reason_codes": list(preflight.policy.reason_codes), "decision": preflight.policy.decision},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INSTALL_BLOCKED",
                "message": preflight.policy.explanation,
                "reason_codes": list(preflight.policy.reason_codes),
                "primary_action": preflight.primary_action,
            },
        )

    await audit_admin_mutation(
        request,
        session,
        action="store.install_requested",
        resource_type="module_store",
        resource_id=f"{module_id}@{version}",
        summary={"site_slug": body.site_slug, "decision": preflight.policy.decision},
    )

    detail = await service.get_module_detail(module_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    if detail.summary.origin == "PUBLIC_MARKETPLACE":
        staging = ArtifactStagingService(session, settings)
        try:
            result = await staging.fetch_release(module_id, version)
        except DistributionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": exc.code.value, "message": str(exc)},
            ) from exc
        package_state = result.state.value
        install_message = result.message
        if result.state == ArtifactState.STAGED:
            artifact_row = await ArtifactRepository(session).get_by_id(result.artifact_id)
            cache_path = artifact_row.cache_path if artifact_row is not None else None
            if cache_path and Path(cache_path).is_file():
                try:
                    mutation = await PackageInstaller(session, settings).install(
                        Path(cache_path),
                        source="marketplace",
                    )
                    package_state = mutation.package_state
                    install_message = mutation.message
                except PackageError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={"code": exc.code, "message": str(exc)},
                    ) from exc
        return InstallResponse(
            success=package_state in {"STAGED", "VERIFIED", "INSTALLED"},
            message=install_message,
            module_id=module_id,
            version=version,
            package_state=package_state,
            artifact_id=result.artifact_id,
            reason_codes=list(result.reason_codes),
        )

    candidates = await service._collect_candidates()
    cand = candidates.get(module_id)
    if cand and cand.catalog_entry_id:
        package_path = resolve_catalog_package(settings, cand.catalog_entry_id)
        if package_path is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog package not found")
        installer = PackageInstaller(session, settings)
        try:
            mutation = await installer.install(package_path, source="catalog")
        except PackageError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        return InstallResponse(
            success=mutation.success,
            message=mutation.message,
            module_id=module_id,
            version=version,
            package_state=mutation.package_state,
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "INSTALL_SOURCE_UNAVAILABLE", "message": "No install source available for this module"},
    )
