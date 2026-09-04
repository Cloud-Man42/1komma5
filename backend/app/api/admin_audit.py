"""Admin audit log API."""

from __future__ import annotations

from app.admin_auth import require_admin_token
from app.deps import get_db_session
from app.schemas import AdminAuditEntryResponse, AdminAuditLogResponse
from energy_core.admin_audit.repo import AdminAuditRepository
from energy_core.admin_audit.service import parse_summary_json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["admin-audit"])


@router.get("/admin/audit-log", response_model=AdminAuditLogResponse)
async def list_admin_audit_log(
    limit: int = Query(default=50, ge=1, le=200),
    site_slug: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> AdminAuditLogResponse:
    rows = await AdminAuditRepository(session).list_recent(limit=limit, site_slug=site_slug)
    return AdminAuditLogResponse(
        entries=[
            AdminAuditEntryResponse(
                id=row.id,
                recorded_at=row.recorded_at,
                http_method=row.http_method,
                path=row.path,
                action=row.action,
                site_slug=row.site_slug,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                outcome=row.outcome,
                summary=parse_summary_json(row.summary_json),
            )
            for row in rows
        ]
    )
