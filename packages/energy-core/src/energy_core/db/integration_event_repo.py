"""Persist and query vehicle integration diagnostic events."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleIntegrationEventModel
from energy_core.vehicles.diagnostics.events import IntegrationEventDraft

logger = logging.getLogger(__name__)

MAX_EVENTS_PER_SITE = 250
RETENTION_DAYS = 14


@dataclass(frozen=True, slots=True)
class IntegrationEventRecord:
    id: int
    site_id: int
    vehicle_id: int | None
    event_type: str
    severity: str
    message: str
    details_json: str
    recorded_at: datetime


class VehicleIntegrationEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_events(
        self,
        *,
        site_id: int,
        vehicle_id: int | None,
        events: tuple[IntegrationEventDraft, ...],
    ) -> None:
        if not events:
            return
        for event in events:
            self._session.add(
                VehicleIntegrationEventModel(
                    site_id=site_id,
                    vehicle_id=vehicle_id,
                    event_type=event.event_type.value,
                    severity=event.severity.value,
                    message=event.message[:512],
                    details_json=event.details_json(),
                    recorded_at=event.recorded_at,
                )
            )
            logger.info(
                "vehicle integration [%s] %s: %s",
                event.severity.value,
                event.event_type.value,
                event.message,
            )
        await self._session.flush()
        await self._prune(site_id)

    async def list_recent(self, *, site_id: int, limit: int = 50) -> list[IntegrationEventRecord]:
        result = await self._session.execute(
            select(VehicleIntegrationEventModel)
            .where(VehicleIntegrationEventModel.site_id == site_id)
            .order_by(VehicleIntegrationEventModel.recorded_at.desc(), VehicleIntegrationEventModel.id.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            IntegrationEventRecord(
                id=row.id,
                site_id=row.site_id,
                vehicle_id=row.vehicle_id,
                event_type=row.event_type,
                severity=row.severity,
                message=row.message,
                details_json=row.details_json,
                recorded_at=row.recorded_at,
            )
            for row in rows
        ]

    async def _prune(self, site_id: int) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
        await self._session.execute(
            delete(VehicleIntegrationEventModel).where(
                VehicleIntegrationEventModel.site_id == site_id,
                VehicleIntegrationEventModel.recorded_at < cutoff,
            )
        )
        result = await self._session.execute(
            select(VehicleIntegrationEventModel.id)
            .where(VehicleIntegrationEventModel.site_id == site_id)
            .order_by(VehicleIntegrationEventModel.recorded_at.desc(), VehicleIntegrationEventModel.id.desc())
            .offset(MAX_EVENTS_PER_SITE)
        )
        stale_ids = [row[0] for row in result.all()]
        if stale_ids:
            await self._session.execute(
                delete(VehicleIntegrationEventModel).where(VehicleIntegrationEventModel.id.in_(stale_ids))
            )
