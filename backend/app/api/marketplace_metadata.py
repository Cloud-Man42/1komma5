"""Admin API for marketplace trust metadata (Step 5C.1 / 5C.1.5)."""

from __future__ import annotations

from datetime import datetime

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_app_settings, get_db_session
from energy_core.config import Settings
from energy_core.platform.modules.marketplace.sync_service import MarketplaceSyncService
from energy_core.platform.modules.marketplace.trust_cache import MarketplaceTrustCacheRepository
from energy_core.platform.modules.marketplace.types import MetadataErrorCode, SyncOutcome
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/modules/marketplace", tags=["marketplace-metadata"])


class MarketplaceStatusResponse(BaseModel):
    enabled: bool
    metadata_health: str
    revocation_freshness: str
    last_sync: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    sync_failed: bool = False
    offline: bool = False
    root_version: int | None = None
    timestamp_version: int | None = None
    snapshot_version: int | None = None
    targets_version: int | None = None
    catalog_age_seconds: float | None = None
    revocation_age_seconds: float | None = None
    cache_generation: int = 0
    catalog_status: str
    revocation_status: str
    revocation_generation: int | None = None


class MarketplaceSyncResponse(BaseModel):
    outcome: str
    message: str
    cache_generation: int | None = None
    error_code: str | None = None


@router.get("/status", response_model=MarketplaceStatusResponse)
async def marketplace_status(
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> MarketplaceStatusResponse:
    repo = MarketplaceTrustCacheRepository(session)
    view = await repo.build_status_view(enabled=settings.marketplace_metadata_enabled)
    return MarketplaceStatusResponse(
        enabled=view.enabled,
        metadata_health=view.metadata_health.value,
        revocation_freshness=view.revocation_freshness.value,
        last_sync=view.last_sync,
        last_success=view.last_success,
        last_error=view.last_error,
        sync_failed=view.sync_failed,
        offline=view.offline,
        root_version=view.root_version,
        timestamp_version=view.timestamp_version,
        snapshot_version=view.snapshot_version,
        targets_version=view.targets_version,
        catalog_age_seconds=view.catalog_age_seconds,
        revocation_age_seconds=view.revocation_age_seconds,
        cache_generation=view.cache_generation,
        catalog_status=view.catalog_status,
        revocation_status=view.revocation_status,
        revocation_generation=view.revocation_generation,
    )


@router.post("/sync", response_model=MarketplaceSyncResponse)
async def marketplace_sync(
    request: Request,
    _: None = Depends(require_admin_token),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> MarketplaceSyncResponse:
    if not settings.marketplace_metadata_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "MARKETPLACE_METADATA_DISABLED", "message": "Marketplace metadata sync is disabled"},
        )
    await audit_admin_mutation(
        request,
        session,
        action="marketplace.sync_started",
        resource_type="marketplace_trust",
        resource_id="default",
    )
    service = MarketplaceSyncService(settings)
    repo = MarketplaceTrustCacheRepository(session)
    row_before = await repo.get_or_create()
    prev_root = row_before.root_version
    prev_revocations = repo.parse_revocations(row_before)
    result, apply_result = await service.sync(session)

    if result.outcome == SyncOutcome.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": MetadataErrorCode.SYNC_IN_PROGRESS.value,
                "message": result.message,
            },
        )

    if result.outcome == SyncOutcome.SUCCESS and apply_result is not None:
        await audit_admin_mutation(
            request,
            session,
            action="marketplace.sync_succeeded",
            resource_type="marketplace_trust",
            resource_id="default",
            summary={"message": result.message},
        )
        if apply_result.root_rotated:
            row_after = await repo.get_or_create()
            await audit_admin_mutation(
                request,
                session,
                action="marketplace.root_rotated",
                resource_type="marketplace_trust",
                resource_id="default",
                summary={"from": prev_root, "to": row_after.root_version},
            )
        if apply_result.revocations_changed:
            await audit_admin_mutation(
                request,
                session,
                action="marketplace.revocation_updated",
                resource_type="marketplace_trust",
                resource_id="default",
                summary={"changed": True},
            )
    elif result.outcome == SyncOutcome.REJECTED:
        summary = {
            "message": result.message,
            "code": result.error_code.value if result.error_code else result.error_category,
        }
        if apply_result is not None and apply_result.rollback is not None:
            summary.update(
                {
                    "reason": "rollback",
                    "role": apply_result.rollback.role,
                    "trusted_version": apply_result.rollback.trusted_version,
                    "incoming_version": apply_result.rollback.incoming_version,
                }
            )
        await audit_admin_mutation(
            request,
            session,
            action="marketplace.metadata_rejected",
            resource_type="marketplace_trust",
            resource_id="default",
            summary=summary,
        )
        await audit_admin_mutation(
            request,
            session,
            action="marketplace.sync_failed",
            resource_type="marketplace_trust",
            resource_id="default",
            summary=summary,
        )
    else:
        await audit_admin_mutation(
            request,
            session,
            action="marketplace.sync_failed",
            resource_type="marketplace_trust",
            resource_id="default",
            summary={
                "message": result.message,
                "code": result.error_code.value if result.error_code else result.error_category,
            },
        )

    row = await MarketplaceTrustCacheRepository(session).get_or_create()
    return MarketplaceSyncResponse(
        outcome=result.outcome.value,
        message=result.message,
        cache_generation=row.cache_generation if result.outcome == SyncOutcome.SUCCESS else None,
        error_code=result.error_code.value if result.error_code else None,
    )
