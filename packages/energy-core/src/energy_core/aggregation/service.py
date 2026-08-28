"""Roll up energy readings into hourly and daily pre-aggregation tables."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo

from energy_core.db.models import EnergyDailyModel, EnergyHourlyModel, EnergyReadingModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession


class EnergyAggregationService:
    def __init__(self, *, is_sqlite: bool) -> None:
        self._is_sqlite = is_sqlite

    async def rollup_site(self, session: AsyncSession, site) -> None:
        await self._rollup_hourly(session, site)
        await self._rollup_daily(session, site)

    async def _rollup_hourly(self, session: AsyncSession, site) -> None:
        now = datetime.now(UTC)
        start = now - timedelta(hours=48)
        stmt = (
            select(EnergyReadingModel)
            .where(
                EnergyReadingModel.site_id == site.id,
                EnergyReadingModel.recorded_at >= start,
                EnergyReadingModel.recorded_at <= now,
            )
            .order_by(EnergyReadingModel.recorded_at)
        )
        readings = (await session.scalars(stmt)).all()
        if len(readings) < 2:
            return

        zone = ZoneInfo(site.timezone)
        hourly: dict[datetime, list[tuple[float, float, float, float]]] = {}
        for previous, current in pairwise(readings):
            started_at = previous.recorded_at
            ended_at = current.recorded_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=UTC)
            seconds = (ended_at - started_at).total_seconds()
            if seconds <= 0 or seconds > 300:
                continue
            hours = seconds / 3600.0
            hour_key = started_at.astimezone(zone).replace(minute=0, second=0, microsecond=0).astimezone(UTC)
            hourly.setdefault(hour_key, []).append(
                (
                    max(0.0, float(previous.solar_production_w or 0.0)) * hours / 1000.0,
                    max(0.0, float(previous.consumption_w or 0.0)) * hours / 1000.0,
                    max(0.0, float(previous.grid_import_w or 0.0)) * hours / 1000.0,
                    max(0.0, float(previous.grid_export_w or 0.0)) * hours / 1000.0,
                )
            )

        insert = sqlite_insert if self._is_sqlite else pg_insert
        for hour, values in hourly.items():
            solar = sum(v[0] for v in values)
            consumption = sum(v[1] for v in values)
            import_kwh = sum(v[2] for v in values)
            export_kwh = sum(v[3] for v in values)
            stmt = insert(EnergyHourlyModel).values(
                site_id=site.id,
                hour=hour,
                solar_kwh=round(solar, 3),
                consumption_kwh=round(consumption, 3),
                import_kwh=round(import_kwh, 3),
                export_kwh=round(export_kwh, 3),
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "hour"],
                set_={
                    "solar_kwh": stmt.excluded.solar_kwh,
                    "consumption_kwh": stmt.excluded.consumption_kwh,
                    "import_kwh": stmt.excluded.import_kwh,
                    "export_kwh": stmt.excluded.export_kwh,
                },
            )
            await session.execute(stmt)

    async def _rollup_daily(self, session: AsyncSession, site) -> None:
        now_local = datetime.now(ZoneInfo(site.timezone))
        day = now_local.date()
        start_local = datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo(site.timezone))
        start_utc = start_local.astimezone(UTC)
        now_utc = now_local.astimezone(UTC)
        stmt = (
            select(EnergyReadingModel)
            .where(
                EnergyReadingModel.site_id == site.id,
                EnergyReadingModel.recorded_at >= start_utc,
                EnergyReadingModel.recorded_at <= now_utc,
            )
            .order_by(EnergyReadingModel.recorded_at)
        )
        readings = (await session.scalars(stmt)).all()
        if len(readings) < 2:
            return
        solar = consumption = import_kwh = export_kwh = 0.0
        for previous, current in pairwise(readings):
            started_at = previous.recorded_at
            ended_at = current.recorded_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=UTC)
            seconds = (ended_at - started_at).total_seconds()
            if seconds <= 0 or seconds > 300:
                continue
            hours = seconds / 3600.0
            solar += max(0.0, float(previous.solar_production_w or 0.0)) * hours / 1000.0
            consumption += max(0.0, float(previous.consumption_w or 0.0)) * hours / 1000.0
            import_kwh += max(0.0, float(previous.grid_import_w or 0.0)) * hours / 1000.0
            export_kwh += max(0.0, float(previous.grid_export_w or 0.0)) * hours / 1000.0

        insert = sqlite_insert if self._is_sqlite else pg_insert
        stmt = insert(EnergyDailyModel).values(
            site_id=site.id,
            day=day,
            solar_kwh=round(solar, 2),
            consumption_kwh=round(consumption, 2),
            import_kwh=round(import_kwh, 2),
            export_kwh=round(export_kwh, 2),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["site_id", "day"],
            set_={
                "solar_kwh": stmt.excluded.solar_kwh,
                "consumption_kwh": stmt.excluded.consumption_kwh,
                "import_kwh": stmt.excluded.import_kwh,
                "export_kwh": stmt.excluded.export_kwh,
            },
        )
        await session.execute(stmt)
