"""Forecast snapshot persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EnergyForecastSnapshotModel
from energy_core.forecast_learning.types import ForecastKind, ForecastSnapshot


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _to_domain(row: EnergyForecastSnapshotModel) -> ForecastSnapshot:
    return ForecastSnapshot(
        period_start=_ensure_utc(row.period_start),
        period_end=_ensure_utc(row.period_end),
        kind=ForecastKind(row.forecast_kind),
        predicted_value=row.predicted_value,
        actual_value=row.actual_value,
        forecast_recorded_at=_ensure_utc(row.forecast_recorded_at),
        actual_recorded_at=_ensure_utc(row.actual_recorded_at) if row.actual_recorded_at else None,
        model_version=row.model_version,
    )


class ForecastSnapshotRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def insert_prediction_if_missing(
        self,
        *,
        site_id: int,
        period_start: datetime,
        period_end: datetime,
        kind: ForecastKind,
        predicted_value: float,
        forecast_recorded_at: datetime,
        model_version: str | None = None,
    ) -> bool:
        insert = sqlite_insert if self._is_sqlite else pg_insert
        values = {
            "site_id": site_id,
            "period_start": _ensure_utc(period_start),
            "period_end": _ensure_utc(period_end),
            "forecast_kind": kind.value,
            "predicted_value": predicted_value,
            "forecast_recorded_at": _ensure_utc(forecast_recorded_at),
            "model_version": model_version,
        }
        stmt = insert(EnergyForecastSnapshotModel).values(**values)
        if self._is_sqlite:
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["site_id", "period_start", "forecast_kind"],
            )
        else:
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["site_id", "period_start", "forecast_kind"],
            )
        result = await self._session.execute(stmt)
        return (result.rowcount or 0) > 0

    async def upsert_prediction(
        self,
        *,
        site_id: int,
        period_start: datetime,
        period_end: datetime,
        kind: ForecastKind,
        predicted_value: float,
        forecast_recorded_at: datetime,
        model_version: str | None = None,
    ) -> None:
        insert = sqlite_insert if self._is_sqlite else pg_insert
        values = {
            "site_id": site_id,
            "period_start": _ensure_utc(period_start),
            "period_end": _ensure_utc(period_end),
            "forecast_kind": kind.value,
            "predicted_value": predicted_value,
            "forecast_recorded_at": _ensure_utc(forecast_recorded_at),
            "model_version": model_version,
        }
        stmt = insert(EnergyForecastSnapshotModel).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id", "period_start", "forecast_kind"],
            set_={
                "period_end": stmt.excluded.period_end,
                "predicted_value": stmt.excluded.predicted_value,
                "forecast_recorded_at": stmt.excluded.forecast_recorded_at,
                "model_version": stmt.excluded.model_version,
            },
        )
        await self._session.execute(stmt)

    async def set_actual(
        self,
        *,
        site_id: int,
        period_start: datetime,
        kind: ForecastKind,
        actual_value: float,
        actual_recorded_at: datetime,
    ) -> bool:
        row = await self._session.scalar(
            select(EnergyForecastSnapshotModel).where(
                EnergyForecastSnapshotModel.site_id == site_id,
                EnergyForecastSnapshotModel.period_start == _ensure_utc(period_start),
                EnergyForecastSnapshotModel.forecast_kind == kind.value,
            )
        )
        if row is None or row.actual_value is not None:
            return False
        row.actual_value = actual_value
        row.actual_recorded_at = _ensure_utc(actual_recorded_at)
        await self._session.flush()
        return True

    async def list_range(
        self,
        site_id: int,
        *,
        start: datetime,
        end: datetime,
        kind: ForecastKind | None = None,
        reconciled_only: bool = False,
    ) -> tuple[ForecastSnapshot, ...]:
        stmt = select(EnergyForecastSnapshotModel).where(
            EnergyForecastSnapshotModel.site_id == site_id,
            EnergyForecastSnapshotModel.period_start >= _ensure_utc(start),
            EnergyForecastSnapshotModel.period_start < _ensure_utc(end),
        )
        if kind is not None:
            stmt = stmt.where(EnergyForecastSnapshotModel.forecast_kind == kind.value)
        if reconciled_only:
            stmt = stmt.where(EnergyForecastSnapshotModel.actual_value.is_not(None))
        stmt = stmt.order_by(EnergyForecastSnapshotModel.period_start.desc())
        rows = await self._session.scalars(stmt)
        return tuple(_to_domain(row) for row in rows)

    async def list_pending_actuals(
        self,
        site_id: int,
        *,
        period_end_before: datetime,
        kind: ForecastKind | None = None,
        limit: int = 500,
    ) -> tuple[ForecastSnapshot, ...]:
        stmt = (
            select(EnergyForecastSnapshotModel)
            .where(
                EnergyForecastSnapshotModel.site_id == site_id,
                EnergyForecastSnapshotModel.period_end <= _ensure_utc(period_end_before),
                EnergyForecastSnapshotModel.actual_value.is_(None),
            )
            .order_by(EnergyForecastSnapshotModel.period_start)
            .limit(limit)
        )
        if kind is not None:
            stmt = stmt.where(EnergyForecastSnapshotModel.forecast_kind == kind.value)
        rows = await self._session.scalars(stmt)
        return tuple(_to_domain(row) for row in rows)
