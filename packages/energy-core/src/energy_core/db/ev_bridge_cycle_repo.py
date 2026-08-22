"""Persistence for EV bridge cycle telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EvBridgeCycleModel


@dataclass(frozen=True, slots=True)
class EvBridgeCycleRecord:
    charger_id: int
    recorded_at: datetime
    applied_current_a: float
    price_kwh: float | None
    policy_mode: str
    decision_reason: str
    override_active: bool
    vehicle_connected: bool | None


class EvBridgeCycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_cycle(
        self,
        *,
        charger_id: int,
        recorded_at: datetime,
        applied_current_a: float,
        price_kwh: float | None,
        policy_mode: str,
        decision_reason: str,
        override_active: bool,
        vehicle_connected: bool | None,
    ) -> EvBridgeCycleModel:
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=UTC)
        row = EvBridgeCycleModel(
            charger_id=charger_id,
            recorded_at=recorded_at,
            applied_current_a=applied_current_a,
            price_kwh=price_kwh,
            policy_mode=policy_mode,
            decision_reason=decision_reason,
            override_active=override_active,
            vehicle_connected=vehicle_connected,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_charger(
        self,
        charger_id: int,
        *,
        from_time: datetime,
        to_time: datetime,
    ) -> list[EvBridgeCycleRecord]:
        if from_time.tzinfo is None:
            from_time = from_time.replace(tzinfo=UTC)
        if to_time.tzinfo is None:
            to_time = to_time.replace(tzinfo=UTC)

        result = await self._session.scalars(
            select(EvBridgeCycleModel)
            .where(
                EvBridgeCycleModel.charger_id == charger_id,
                EvBridgeCycleModel.recorded_at >= from_time,
                EvBridgeCycleModel.recorded_at <= to_time,
            )
            .order_by(EvBridgeCycleModel.recorded_at)
        )
        return [self._to_record(row) for row in result]

    async def list_starts_since(
        self,
        charger_id: int,
        *,
        since: datetime,
    ) -> list[datetime]:
        if since.tzinfo is None:
            since = since.replace(tzinfo=UTC)
        result = await self._session.scalars(
            select(EvBridgeCycleModel)
            .where(
                EvBridgeCycleModel.charger_id == charger_id,
                EvBridgeCycleModel.recorded_at >= since,
            )
            .order_by(EvBridgeCycleModel.recorded_at)
        )
        starts: list[datetime] = []
        previous_current = 0.0
        for row in result:
            if row.applied_current_a > 0 and previous_current <= 0:
                starts.append(row.recorded_at)
            previous_current = row.applied_current_a
        return starts

    @staticmethod
    def _to_record(row: EvBridgeCycleModel) -> EvBridgeCycleRecord:
        return EvBridgeCycleRecord(
            charger_id=row.charger_id,
            recorded_at=row.recorded_at,
            applied_current_a=row.applied_current_a,
            price_kwh=row.price_kwh,
            policy_mode=row.policy_mode,
            decision_reason=row.decision_reason,
            override_active=row.override_active,
            vehicle_connected=row.vehicle_connected,
        )
