"""Health aggregation over integration health records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.contracts.health import HealthStatus, from_energy_provider_status
from energy_core.db.models import IntegrationHealthModel
from energy_core.integrations.health import IntegrationHealthRecorder


@dataclass(frozen=True, slots=True)
class ProviderHealthRecord:
    provider: str
    status: HealthStatus
    last_success_at: datetime | None
    last_attempt_at: datetime | None
    consecutive_failures: int
    stale_seconds: float | None


class HealthAggregator:
    """Wraps existing IntegrationHealthRecorder with unified HealthStatus."""

    def __init__(self, session: AsyncSession, *, is_sqlite: bool) -> None:
        self._session = session
        self._recorder = IntegrationHealthRecorder(session, is_sqlite=is_sqlite)

    @property
    def recorder(self) -> IntegrationHealthRecorder:
        return self._recorder

    async def list_for_site(self, site_id: int) -> tuple[ProviderHealthRecord, ...]:
        rows = (
            await self._session.scalars(
                select(IntegrationHealthModel).where(IntegrationHealthModel.site_id == site_id)
            )
        ).all()
        return tuple(
            ProviderHealthRecord(
                provider=row.provider,
                status=from_energy_provider_status(row.status),
                last_success_at=row.last_success_at,
                last_attempt_at=row.last_attempt_at,
                consecutive_failures=row.consecutive_failures,
                stale_seconds=row.stale_seconds,
            )
            for row in rows
        )

    async def overall_status(self, site_id: int) -> HealthStatus:
        records = await self.list_for_site(site_id)
        if not records:
            return HealthStatus.UNAVAILABLE
        if all(record.status == HealthStatus.HEALTHY for record in records):
            return HealthStatus.HEALTHY
        if any(record.status == HealthStatus.HEALTHY for record in records):
            return HealthStatus.DEGRADED
        if any(record.status == HealthStatus.DISABLED for record in records):
            return HealthStatus.DISABLED
        return HealthStatus.UNAVAILABLE
