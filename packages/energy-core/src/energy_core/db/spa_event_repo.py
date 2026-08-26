"""Repository for spa energy events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SpaEnergyEventModel


@dataclass(frozen=True, slots=True)
class SpaEnergyEventRecord:
    id: int
    consumer_id: int
    timestamp: datetime
    event_type: str
    start_time: datetime | None
    stop_time: datetime | None
    runtime_seconds: float | None
    estimated_kwh: float | None
    actual_kwh: float | None
    estimated_cost: float | None
    actual_cost: float | None
    solar_share: float | None
    battery_share: float | None
    grid_share: float | None
    reason: str
    reason_sv: str
    strategy: str
    decision_score: float | None
    manual_override: bool
    dry_run: bool
    shadow: bool


class SpaEnergyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(
        self,
        *,
        consumer_id: int,
        timestamp: datetime,
        event_type: str,
        reason: str,
        reason_sv: str,
        strategy: str,
        start_time: datetime | None = None,
        stop_time: datetime | None = None,
        runtime_seconds: float | None = None,
        estimated_kwh: float | None = None,
        actual_kwh: float | None = None,
        estimated_cost: float | None = None,
        actual_cost: float | None = None,
        solar_share: float | None = None,
        battery_share: float | None = None,
        grid_share: float | None = None,
        decision_score: float | None = None,
        manual_override: bool = False,
        dry_run: bool = True,
        shadow: bool = False,
    ) -> SpaEnergyEventRecord:
        model = SpaEnergyEventModel(
            consumer_id=consumer_id,
            timestamp=timestamp,
            event_type=event_type,
            start_time=start_time,
            stop_time=stop_time,
            runtime_seconds=runtime_seconds,
            estimated_kwh=estimated_kwh,
            actual_kwh=actual_kwh,
            estimated_cost=estimated_cost,
            actual_cost=actual_cost,
            solar_share=solar_share,
            battery_share=battery_share,
            grid_share=grid_share,
            reason=reason,
            reason_sv=reason_sv,
            strategy=strategy,
            decision_score=decision_score,
            manual_override=manual_override,
            dry_run=dry_run,
            shadow=shadow,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_record(model)

    async def list_for_consumer(
        self,
        consumer_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SpaEnergyEventRecord]:
        result = await self._session.scalars(
            select(SpaEnergyEventModel)
            .where(SpaEnergyEventModel.consumer_id == consumer_id)
            .order_by(desc(SpaEnergyEventModel.timestamp))
            .limit(limit)
            .offset(offset)
        )
        return [self._to_record(row) for row in result]

    def _to_record(self, model: SpaEnergyEventModel) -> SpaEnergyEventRecord:
        return SpaEnergyEventRecord(
            id=model.id,
            consumer_id=model.consumer_id,
            timestamp=model.timestamp,
            event_type=model.event_type,
            start_time=model.start_time,
            stop_time=model.stop_time,
            runtime_seconds=model.runtime_seconds,
            estimated_kwh=model.estimated_kwh,
            actual_kwh=model.actual_kwh,
            estimated_cost=model.estimated_cost,
            actual_cost=model.actual_cost,
            solar_share=model.solar_share,
            battery_share=model.battery_share,
            grid_share=model.grid_share,
            reason=model.reason,
            reason_sv=model.reason_sv,
            strategy=model.strategy,
            decision_score=model.decision_score,
            manual_override=model.manual_override,
            dry_run=model.dry_run,
            shadow=model.shadow,
        )
