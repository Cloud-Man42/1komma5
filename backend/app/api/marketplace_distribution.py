"""Admin API for remote artifact staging and supply-chain security (Step 5C.3 / 5C.4)."""

from __future__ import annotations

import json
from datetime import datetime

from app.admin_audit_helpers import audit_admin_mutation
from app.user_auth import require_permission
from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.platform.modules.distribution.artifact_repository import ArtifactRepository
from energy_core.platform.modules.distribution.catalog_resolver import CatalogReleaseResolver
from energy_core.platform.modules.distribution.staging_service import ArtifactStagingService
from energy_core.platform.modules.distribution.types import DistributionError
from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/marketplace", tags=["marketplace-distribution"])

_fetch_in_progress: set[str] = set()


class CatalogReleaseItem(BaseModel):
    module_id: str
    publisher_id: str
    version: str
    release_id: str
    content_sha256: str | None = None
    artifact_size: int | None = None
    source: str


class CatalogResponse(BaseModel):
    releases: list[CatalogReleaseItem]
    catalog_version: int | None = None


class ArtifactSummary(BaseModel):
    id: int
    module_id: str
    publisher_id: str
    version: str
    release_id: str
    content_sha256: str
    state: str
    source_type: str
    reason_codes: list[str] = []
    cache_path: str | None = None
    quarantine_path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ArtifactSecurityResponse(BaseModel):
    artifact_id: int
    integrity_verified: bool
    sbom_status: str
    advisory_status: str
    highest_severity: str
    vulnerability_count: int
    critical_count: int
    high_count: int
    security_review_required: bool
    policy_decision: str | None = None
    reason_codes: list[str] = []
    vulnerabilities: list[dict] = []
    runtime_blocked: bool = True
    runtime_message: str = "Runtime: BLOCKED until Step 5C.5"


class FetchResponse(BaseModel):
    artifact_id: int
    state: str
    reason_codes: list[str] = []
    security_status: str | None = None
    policy_decision: str | None = None
    message: str


@router.get("/catalog", response_model=CatalogResponse)
async def list_catalog_releases(
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> CatalogResponse:
    if not settings.marketplace_metadata_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MARKETPLACE_METADATA_DISABLED", "message": "Marketplace metadata is disabled"},
        )
    row = await MarketplaceTrustCacheRepository(session).get_or_create()
    if not row.catalog_json:
        return CatalogResponse(releases=[], catalog_version=None)
    resolver = CatalogReleaseResolver.from_cache_json(row.catalog_json)
    releases = [
        CatalogReleaseItem(
            module_id=item["module_id"],
            publisher_id=item["publisher_id"],
            version=item["version"],
            release_id=item["release_id"],
            content_sha256=item.get("content_sha256"),
            artifact_size=item.get("artifact_size"),
            source=item.get("source", "PUBLIC"),
        )
        for item in resolver.list_modules()
    ]
    catalog_version = json.loads(row.catalog_json).get("snapshot", {}).get("version")
    return CatalogResponse(releases=releases, catalog_version=catalog_version)


@router.get("/releases/{module_id}", response_model=CatalogResponse)
async def list_module_releases(
    module_id: str,
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> CatalogResponse:
    catalog = await list_catalog_releases(_, session, settings)
    filtered = [r for r in catalog.releases if r.module_id == module_id]
    return CatalogResponse(releases=filtered, catalog_version=catalog.catalog_version)


@router.post("/releases/{module_id}/{version}/fetch", response_model=FetchResponse)
async def fetch_release(
    module_id: str,
    version: str,
    request: Request,
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> FetchResponse:
    if not settings.marketplace_metadata_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MARKETPLACE_METADATA_DISABLED", "message": "Marketplace metadata is disabled"},
        )
    key = f"{module_id}@{version}"
    if key in _fetch_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "FETCH_IN_PROGRESS", "message": f"Fetch already in progress for {key}"},
        )
    _fetch_in_progress.add(key)
    try:
        await audit_admin_mutation(
            request,
            session,
            action="marketplace.artifact_download_started",
            resource_type="marketplace_artifact",
            resource_id=key,
        )
        service = ArtifactStagingService(session, settings)
        try:
            result = await service.fetch_release(module_id, version)
        except DistributionError as exc:
            await audit_admin_mutation(
                request,
                session,
                action="marketplace.artifact_rejected",
                resource_type="marketplace_artifact",
                resource_id=key,
                summary={"code": exc.code.value, "message": str(exc)},
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": exc.code.value, "message": str(exc)},
            ) from exc

        action = {
            "STAGED": "marketplace.artifact_verified",
            "QUARANTINED": "marketplace.artifact_quarantined",
        }.get(result.state.value, "marketplace.artifact_completed")
        await audit_admin_mutation(
            request,
            session,
            action=action,
            resource_type="marketplace_artifact",
            resource_id=str(result.artifact_id),
            summary={"state": result.state.value, "reason_codes": list(result.reason_codes)},
        )
        return FetchResponse(
            artifact_id=result.artifact_id,
            state=result.state.value,
            reason_codes=list(result.reason_codes),
            security_status=result.security_status,
            policy_decision=result.policy_decision,
            message=result.message,
        )
    finally:
        _fetch_in_progress.discard(key)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactSummary)
async def get_artifact(
    artifact_id: int,
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> ArtifactSummary:
    repo = ArtifactRepository(session)
    row = await repo.get_by_id(artifact_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    reason_codes: list[str] = []
    if row.reason_codes_json:
        reason_codes = json.loads(row.reason_codes_json)
    return ArtifactSummary(
        id=row.id,
        module_id=row.module_id,
        publisher_id=row.publisher_id,
        version=row.version,
        release_id=row.release_id,
        content_sha256=row.content_sha256,
        state=row.state,
        source_type=row.source_type,
        reason_codes=reason_codes,
        cache_path=row.cache_path,
        quarantine_path=row.quarantine_path,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/artifacts/{artifact_id}/security", response_model=ArtifactSecurityResponse)
async def get_artifact_security(
    artifact_id: int,
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> ArtifactSecurityResponse:
    from sqlalchemy import select

    from energy_core.db.models.marketplace_distribution import (
        MarketplaceArtifactSecurityModel,
        MarketplaceReleaseVulnerabilityModel,
    )

    repo = ArtifactRepository(session)
    artifact = await repo.get_by_id(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    sec = await session.scalar(
        select(MarketplaceArtifactSecurityModel).where(MarketplaceArtifactSecurityModel.artifact_id == artifact_id)
    )
    if sec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security snapshot not found")
    vulns = list(
        await session.scalars(
            select(MarketplaceReleaseVulnerabilityModel).where(
                MarketplaceReleaseVulnerabilityModel.artifact_id == artifact_id
            )
        )
    )
    reason_codes = json.loads(sec.reason_codes_json or "[]")
    snapshot = json.loads(sec.snapshot_json or "{}")
    vulnerabilities = snapshot.get("vulnerabilities") or [
        {
            "advisory_id": v.advisory_id,
            "component_name": v.component_name,
            "component_version": v.component_version,
            "purl": v.purl,
            "severity": v.severity,
            "matched": v.matched,
            "version_status": v.version_status,
        }
        for v in vulns
    ]
    return ArtifactSecurityResponse(
        artifact_id=artifact_id,
        integrity_verified=sec.integrity_verified,
        sbom_status=sec.sbom_status,
        advisory_status=sec.advisory_status,
        highest_severity=sec.highest_severity,
        vulnerability_count=sec.vulnerability_count,
        critical_count=sec.critical_count,
        high_count=sec.high_count,
        security_review_required=sec.security_review_required,
        policy_decision=sec.policy_decision,
        reason_codes=reason_codes,
        vulnerabilities=vulnerabilities,
    )


@router.get("/quarantine", response_model=list[ArtifactSummary])
async def list_quarantined_artifacts(
    _: None = Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
) -> list[ArtifactSummary]:
    repo = ArtifactRepository(session)
    rows = await repo.list_quarantined()
    result: list[ArtifactSummary] = []
    for row in rows:
        reason_codes = json.loads(row.reason_codes_json or "[]")
        result.append(
            ArtifactSummary(
                id=row.id,
                module_id=row.module_id,
                publisher_id=row.publisher_id,
                version=row.version,
                release_id=row.release_id,
                content_sha256=row.content_sha256,
                state=row.state,
                source_type=row.source_type,
                reason_codes=reason_codes,
                cache_path=row.cache_path,
                quarantine_path=row.quarantine_path,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return result
