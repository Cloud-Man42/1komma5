"""ChargeFinder integration status singleton persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import ChargeFinderIntegrationStatusModel


@dataclass(frozen=True, slots=True)
class ChargeFinderIntegrationStatusRecord:
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_lookup_at: datetime | None
    last_latency_ms: int | None
    consecutive_failures: int
    last_error: str | None
    cache_hits: int
    cache_misses: int
    parser_failures: int
    blocked_until: datetime | None
    browser_status: str | None
    parsing_version: str


class ChargeFinderIntegrationStatusRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> ChargeFinderIntegrationStatusRecord:
        row = await self._ensure_row()
        return _to_record(row)

    async def record_success(self, *, latency_ms: int, lookup_mode: str | None = None) -> None:
        row = await self._ensure_row()
        now = datetime.now(UTC)
        row.last_success_at = now
        row.last_lookup_at = now
        row.last_latency_ms = latency_ms
        row.consecutive_failures = 0
        row.last_error = None
        row.parser_failures = 0
        row.blocked_until = None
        if lookup_mode:
            row.lookup_mode = lookup_mode
        await self._session.flush()

    async def record_failure(
        self,
        *,
        error: str | None,
        latency_ms: int | None = None,
        lookup_mode: str | None = None,
        parser_failure: bool = False,
        blocked_until: datetime | None = None,
    ) -> None:
        row = await self._ensure_row()
        now = datetime.now(UTC)
        row.last_failure_at = now
        row.last_lookup_at = now
        row.consecutive_failures += 1
        row.last_error = (error or "")[:512] or None
        if latency_ms is not None:
            row.last_latency_ms = latency_ms
        if lookup_mode:
            row.lookup_mode = lookup_mode
        if parser_failure:
            row.parser_failures += 1
        if blocked_until is not None:
            row.blocked_until = blocked_until
        await self._session.flush()

    async def record_cache_hit(self) -> None:
        row = await self._ensure_row()
        row.cache_hits += 1
        await self._session.flush()

    async def record_cache_miss(self) -> None:
        row = await self._ensure_row()
        row.cache_misses += 1
        await self._session.flush()

    async def _ensure_row(self) -> ChargeFinderIntegrationStatusModel:
        row = await self._session.scalar(select(ChargeFinderIntegrationStatusModel).limit(1))
        if row is None:
            row = ChargeFinderIntegrationStatusModel()
            self._session.add(row)
            await self._session.flush()
        return row


def _to_record(row: ChargeFinderIntegrationStatusModel) -> ChargeFinderIntegrationStatusRecord:
    return ChargeFinderIntegrationStatusRecord(
        last_success_at=row.last_success_at,
        last_failure_at=row.last_failure_at,
        last_lookup_at=row.last_lookup_at,
        last_latency_ms=row.last_latency_ms,
        consecutive_failures=row.consecutive_failures,
        last_error=row.last_error,
        cache_hits=row.cache_hits,
        cache_misses=row.cache_misses,
        parser_failures=row.parser_failures,
        blocked_until=row.blocked_until,
        browser_status=row.browser_status,
        parsing_version=row.parsing_version,
    )
