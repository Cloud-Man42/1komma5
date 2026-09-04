"""Admin audit log repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from energy_core.db.models import AdminAuditLogModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AdminAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        http_method: str,
        path: str,
        action: str,
        outcome: str,
        site_slug: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        summary: dict | None = None,
    ) -> AdminAuditLogModel:
        row = AdminAuditLogModel(
            recorded_at=datetime.now(UTC),
            http_method=http_method,
            path=path,
            action=action,
            site_slug=site_slug,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            summary_json=json.dumps(summary, ensure_ascii=False, default=str) if summary else None,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_recent(
        self,
        *,
        limit: int = 50,
        site_slug: str | None = None,
    ) -> tuple[AdminAuditLogModel, ...]:
        stmt = select(AdminAuditLogModel).order_by(AdminAuditLogModel.recorded_at.desc()).limit(limit)
        if site_slug:
            stmt = stmt.where(AdminAuditLogModel.site_slug == site_slug)
        result = await self._session.scalars(stmt)
        return tuple(result.all())
