"""Persisted solar forecast API response snapshots."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.db.models import SolarForecastApiSnapshotModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


def _freshness_from_age(age_seconds: float, *, stale_after_seconds: float) -> str:
    if age_seconds <= 120:
        return "LIVE"
    if age_seconds <= stale_after_seconds:
        return "FRESH"
    if age_seconds <= stale_after_seconds * 3:
        return "STALE"
    return "DEGRADED"


class SolarForecastApiSnapshotRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert(
        self,
        site_id: int,
        payload: dict[str, Any],
        *,
        forecast_generated_at: datetime | None = None,
        stale_after_seconds: float = 1800.0,
    ) -> None:
        now = datetime.now(UTC)
        forecast_at = forecast_generated_at
        if forecast_at is None:
            raw = payload.get("generated_at")
            if isinstance(raw, str):
                forecast_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            elif isinstance(raw, datetime):
                forecast_at = raw

        age = 0.0
        if forecast_at is not None:
            if forecast_at.tzinfo is None:
                forecast_at = forecast_at.replace(tzinfo=UTC)
            age = max(0.0, (now - forecast_at.astimezone(UTC)).total_seconds())

        freshness = _freshness_from_age(age, stale_after_seconds=stale_after_seconds)
        payload = {
            **payload,
            "age_seconds": age,
            "freshness": freshness,
            "stale": freshness in {"STALE", "DEGRADED"},
        }

        values = {
            "site_id": site_id,
            "generated_at": now,
            "forecast_generated_at": forecast_at,
            "freshness": freshness,
            "payload_json": json.dumps(payload, default=str),
        }
        insert = sqlite_insert if self._is_sqlite else pg_insert
        stmt = insert(SolarForecastApiSnapshotModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id"],
            set_={
                "generated_at": stmt.excluded.generated_at,
                "forecast_generated_at": stmt.excluded.forecast_generated_at,
                "freshness": stmt.excluded.freshness,
                "payload_json": stmt.excluded.payload_json,
            },
        )
        await self._session.execute(stmt)

    async def get_for_site(self, site_id: int, *, stale_after_seconds: float = 1800.0) -> dict[str, Any] | None:
        row = await self._session.scalar(
            select(SolarForecastApiSnapshotModel).where(
                SolarForecastApiSnapshotModel.site_id == site_id
            )
        )
        if row is None:
            return None

        payload = json.loads(row.payload_json)
        now = datetime.now(UTC)
        forecast_at = row.forecast_generated_at
        if forecast_at is None:
            raw = payload.get("generated_at")
            if isinstance(raw, str):
                forecast_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))

        age = 0.0
        if forecast_at is not None:
            if forecast_at.tzinfo is None:
                forecast_at = forecast_at.replace(tzinfo=UTC)
            age = max(0.0, (now - forecast_at.astimezone(UTC)).total_seconds())

        freshness = _freshness_from_age(age, stale_after_seconds=stale_after_seconds)
        payload["generated_at"] = (
            forecast_at.isoformat() if forecast_at is not None else payload.get("generated_at")
        )
        payload["age_seconds"] = age
        payload["freshness"] = freshness
        payload["stale"] = freshness in {"STALE", "DEGRADED"}
        payload["snapshot_generated_at"] = row.generated_at.astimezone(UTC).isoformat()
        return payload
