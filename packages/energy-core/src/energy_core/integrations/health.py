"""Integration health recording and query."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.db.models import IntegrationHealthModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


class IntegrationHealthRecorder:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def record_success(
        self,
        site_id: int,
        provider: str,
        *,
        latency_ms: float | None = None,
        circuit_breaker_state: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        await self._upsert(
            site_id,
            provider,
            {
                "status": "ok",
                "last_success_at": now,
                "last_attempt_at": now,
                "latency_ms": latency_ms,
                "consecutive_failures": 0,
                "stale_seconds": 0.0,
                "circuit_breaker_state": circuit_breaker_state,
                "last_error_class": None,
            },
        )

    async def record_failure(
        self,
        site_id: int,
        provider: str,
        *,
        error_class: str,
        latency_ms: float | None = None,
        circuit_breaker_state: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        existing = await self._session.scalar(
            select(IntegrationHealthModel).where(
                IntegrationHealthModel.site_id == site_id,
                IntegrationHealthModel.provider == provider,
            )
        )
        failures = (existing.consecutive_failures + 1) if existing else 1
        stale_seconds = None
        if existing and existing.last_success_at:
            stale_seconds = max(0.0, (now - existing.last_success_at.astimezone(UTC)).total_seconds())
        await self._upsert(
            site_id,
            provider,
            {
                "status": "error",
                "last_success_at": existing.last_success_at if existing else None,
                "last_attempt_at": now,
                "latency_ms": latency_ms,
                "consecutive_failures": failures,
                "stale_seconds": stale_seconds,
                "circuit_breaker_state": circuit_breaker_state,
                "last_error_class": error_class[:128],
            },
        )

    async def _upsert(self, site_id: int, provider: str, values: dict[str, Any]) -> None:
        payload = {"site_id": site_id, "provider": provider, **values}
        insert = sqlite_insert if self._is_sqlite else pg_insert
        stmt = insert(IntegrationHealthModel).values(**payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id", "provider"],
            set_={key: getattr(stmt.excluded, key) for key in values},
        )
        await self._session.execute(stmt)

    async def list_for_site(self, site_id: int) -> list[dict[str, Any]]:
        rows = (
            await self._session.scalars(
                select(IntegrationHealthModel)
                .where(IntegrationHealthModel.site_id == site_id)
                .order_by(IntegrationHealthModel.provider)
            )
        ).all()
        now = datetime.now(UTC)
        result = []
        for row in rows:
            stale = row.stale_seconds
            if stale is None and row.last_success_at:
                stale = max(0.0, (now - row.last_success_at.astimezone(UTC)).total_seconds())
            status = row.status
            if stale is not None and stale > 300 and status == "ok":
                status = "stale"
            result.append(
                {
                    "provider": row.provider,
                    "status": status,
                    "last_success_at": row.last_success_at.isoformat() if row.last_success_at else None,
                    "last_attempt_at": row.last_attempt_at.isoformat() if row.last_attempt_at else None,
                    "latency_ms": row.latency_ms,
                    "consecutive_failures": row.consecutive_failures,
                    "stale_seconds": stale,
                    "circuit_breaker_state": row.circuit_breaker_state,
                    "last_error_class": row.last_error_class,
                }
            )
        return result
