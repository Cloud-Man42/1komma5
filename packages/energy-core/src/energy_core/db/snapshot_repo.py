"""Site live snapshot persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from energy_core.db.models import SiteLiveSnapshotModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


class SiteLiveSnapshotRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert(self, site_id: int, payload: dict[str, Any]) -> None:
        generated_at_raw = payload.get("generated_at")
        generated_at = (
            datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))
            if isinstance(generated_at_raw, str)
            else datetime.now(UTC)
        )
        values = {
            "site_id": site_id,
            "generated_at": generated_at,
            "freshness": payload.get("freshness", "DEGRADED"),
            "source_status_json": json.dumps(payload.get("source_status", {})),
            "payload_json": json.dumps(payload),
        }
        insert = sqlite_insert if self._is_sqlite else pg_insert
        stmt = insert(SiteLiveSnapshotModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id"],
            set_={
                "generated_at": stmt.excluded.generated_at,
                "freshness": stmt.excluded.freshness,
                "source_status_json": stmt.excluded.source_status_json,
                "payload_json": stmt.excluded.payload_json,
            },
        )
        await self._session.execute(stmt)

    async def get_for_site(self, site_id: int) -> dict[str, Any] | None:
        row = await self._session.scalar(
            select(SiteLiveSnapshotModel).where(SiteLiveSnapshotModel.site_id == site_id)
        )
        if row is None:
            return None
        payload = json.loads(row.payload_json)
        payload["generated_at"] = row.generated_at.isoformat()
        payload["freshness"] = row.freshness
        payload["source_status"] = json.loads(row.source_status_json)
        age = int((datetime.now(UTC) - row.generated_at.astimezone(UTC)).total_seconds())
        payload["age_seconds"] = max(0, age)
        return payload
