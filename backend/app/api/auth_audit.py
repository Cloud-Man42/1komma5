"""Auth audit log API."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_db_session
from app.user_auth import require_permission
from energy_core.auth.repos.auth_audit_repo import AuthAuditRepository
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin/auth-audit", tags=["auth-audit"])


@router.get("")
async def list_auth_audit(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _principal=Depends(require_permission("audit.read")),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int | None = None,
    event_type: str | None = None,
    site_id: int | None = None,
    success: bool | None = None,
) -> dict:
    rows = await AuthAuditRepository(session).list_recent(
        limit=limit,
        user_id=user_id,
        event_type=event_type,
        site_id=site_id,
        success=success,
    )
    return {
        "events": [
            {
                "id": row.id,
                "recordedAt": row.recorded_at.isoformat(),
                "userId": row.user_id,
                "username": row.username,
                "eventType": row.event_type,
                "entityType": row.entity_type,
                "entityId": row.entity_id,
                "siteId": row.site_id,
                "action": row.action,
                "success": row.success,
                "sourceIp": row.source_ip,
            }
            for row in rows
        ]
    }
