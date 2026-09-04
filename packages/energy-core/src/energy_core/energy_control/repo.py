"""Control action persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EnergyControlActionModel
from energy_core.energy_control.types import (
    ControlActionRecord,
    ControlOutcome,
    ControlResult,
    ControlTarget,
    OptimizationAction,
)
from energy_core.price_engine.types import OptimizationMode


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _to_domain(row: EnergyControlActionModel) -> ControlActionRecord:
    payload: dict = {}
    if row.payload_json:
        try:
            payload = json.loads(row.payload_json)
        except json.JSONDecodeError:
            payload = {}
    return ControlActionRecord(
        id=row.id,
        site_id=row.site_id,
        recorded_at=_ensure_utc(row.recorded_at),
        optimization_mode=OptimizationMode(row.optimization_mode),
        action=OptimizationAction(row.action),
        target=ControlTarget(row.target),
        outcome=ControlOutcome(row.outcome),
        dry_run=bool(row.dry_run),
        reason=row.reason,
        payload=payload,
    )


class ControlActionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        site_id: int,
        optimization_mode: OptimizationMode,
        result: ControlResult,
        recorded_at: datetime | None = None,
    ) -> ControlActionRecord:
        row = EnergyControlActionModel(
            site_id=site_id,
            recorded_at=_ensure_utc(recorded_at or datetime.now(UTC)),
            optimization_mode=optimization_mode.value,
            action=result.action.value,
            target=result.target.value,
            outcome=result.outcome.value,
            dry_run=result.dry_run,
            reason=result.reason_sv or result.reason,
            payload_json=json.dumps(result.payload) if result.payload else None,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_domain(row)

    async def latest(self, site_id: int) -> ControlActionRecord | None:
        row = await self._session.scalar(
            select(EnergyControlActionModel)
            .where(EnergyControlActionModel.site_id == site_id)
            .order_by(desc(EnergyControlActionModel.recorded_at))
            .limit(1)
        )
        return _to_domain(row) if row else None

    async def list_recent(self, site_id: int, *, limit: int = 20) -> tuple[ControlActionRecord, ...]:
        rows = await self._session.scalars(
            select(EnergyControlActionModel)
            .where(EnergyControlActionModel.site_id == site_id)
            .order_by(desc(EnergyControlActionModel.recorded_at))
            .limit(limit)
        )
        return tuple(_to_domain(row) for row in rows)
