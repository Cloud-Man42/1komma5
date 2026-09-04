"""FastAPI helper for admin audit logging."""

from __future__ import annotations

from typing import Any

from energy_core.admin_audit.service import record_admin_audit
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def audit_admin_mutation(
    request: Request,
    session: AsyncSession,
    *,
    action: str,
    site_slug: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    await record_admin_audit(
        session,
        http_method=request.method,
        path=request.url.path,
        action=action,
        site_slug=site_slug,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=summary,
    )
