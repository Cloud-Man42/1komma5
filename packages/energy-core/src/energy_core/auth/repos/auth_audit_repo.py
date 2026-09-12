"""Auth-specific audit event repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from energy_core.db.models import EmicAuthAuditEventModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class AuthAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        event_type: str,
        action: str,
        success: bool,
        user_id: int | None = None,
        username: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        site_id: int | None = None,
        source_ip: str | None = None,
        metadata: dict | None = None,
    ) -> EmicAuthAuditEventModel:
        row = EmicAuthAuditEventModel(
            recorded_at=datetime.now(UTC),
            user_id=user_id,
            username=username,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            site_id=site_id,
            action=action,
            success=success,
            source_ip=source_ip,
            metadata_json=json.dumps(metadata, ensure_ascii=False, default=str) if metadata else None,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_recent(
        self,
        *,
        limit: int = 100,
        user_id: int | None = None,
        event_type: str | None = None,
        site_id: int | None = None,
        success: bool | None = None,
    ) -> tuple[EmicAuthAuditEventModel, ...]:
        stmt = select(EmicAuthAuditEventModel).order_by(EmicAuthAuditEventModel.recorded_at.desc()).limit(limit)
        if user_id is not None:
            stmt = stmt.where(EmicAuthAuditEventModel.user_id == user_id)
        if event_type is not None:
            stmt = stmt.where(EmicAuthAuditEventModel.event_type == event_type)
        if site_id is not None:
            stmt = stmt.where(EmicAuthAuditEventModel.site_id == site_id)
        if success is not None:
            stmt = stmt.where(EmicAuthAuditEventModel.success.is_(success))
        rows = await self._session.scalars(stmt)
        return tuple(rows.all())
