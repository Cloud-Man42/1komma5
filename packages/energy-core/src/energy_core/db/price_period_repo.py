"""Price engine persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import PriceEngineStateModel, PricePeriodModel
from energy_core.price_engine.types import (
    Currency,
    OptimizationMode,
    PriceArea,
    PriceEngineStatus,
    PricePeriod,
    PriceQuality,
    PriceSource,
)


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _to_domain(row: PricePeriodModel) -> PricePeriod:
    components = {}
    if row.components_json:
        try:
            components = json.loads(row.components_json)
        except json.JSONDecodeError:
            components = {}
    return PricePeriod(
        period_start=_ensure_utc(row.period_start),
        period_end=_ensure_utc(row.period_end),
        site_id=row.site_id,
        price_area=PriceArea(row.price_area),
        currency=Currency(row.currency),
        market_price_sek_kwh=row.market_price_sek_kwh,
        import_price_sek_kwh=row.import_price_sek_kwh,
        export_price_sek_kwh=row.export_price_sek_kwh,
        source=PriceSource(row.source),
        quality=PriceQuality(row.quality),
        is_estimated=bool(row.is_estimated),
        components=components,
    )


class PricePeriodRepository:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert_periods(self, periods: tuple[PricePeriod, ...]) -> int:
        if not periods:
            return 0
        insert = sqlite_insert if self._is_sqlite else pg_insert
        count = 0
        for period in periods:
            values = {
                "site_id": period.site_id,
                "period_start": period.period_start,
                "period_end": period.period_end,
                "price_area": period.price_area.value,
                "currency": period.currency.value,
                "market_price_sek_kwh": period.market_price_sek_kwh,
                "import_price_sek_kwh": period.import_price_sek_kwh,
                "export_price_sek_kwh": period.export_price_sek_kwh,
                "source": period.source.value,
                "quality": period.quality.value,
                "is_estimated": period.is_estimated,
                "components_json": json.dumps(period.components) if period.components else None,
            }
            stmt = insert(PricePeriodModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "period_start"],
                set_={
                    "period_end": stmt.excluded.period_end,
                    "price_area": stmt.excluded.price_area,
                    "currency": stmt.excluded.currency,
                    "market_price_sek_kwh": stmt.excluded.market_price_sek_kwh,
                    "import_price_sek_kwh": stmt.excluded.import_price_sek_kwh,
                    "export_price_sek_kwh": stmt.excluded.export_price_sek_kwh,
                    "source": stmt.excluded.source,
                    "quality": stmt.excluded.quality,
                    "is_estimated": stmt.excluded.is_estimated,
                    "components_json": stmt.excluded.components_json,
                },
            )
            await self._session.execute(stmt)
            count += 1
        return count

    async def list_range(
        self,
        site_id: int,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[PricePeriod, ...]:
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        rows = await self._session.scalars(
            select(PricePeriodModel)
            .where(
                PricePeriodModel.site_id == site_id,
                PricePeriodModel.period_start >= start,
                PricePeriodModel.period_start < end,
            )
            .order_by(PricePeriodModel.period_start)
        )
        return tuple(_to_domain(row) for row in rows)

    async def get_at(self, site_id: int, period_start: datetime) -> PricePeriod | None:
        if period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=UTC)
        row = await self._session.scalar(
            select(PricePeriodModel).where(
                PricePeriodModel.site_id == site_id,
                PricePeriodModel.period_start == period_start,
            )
        )
        return _to_domain(row) if row else None

    async def delete_older_than(self, site_id: int, cutoff: datetime) -> int:
        result = await self._session.execute(
            delete(PricePeriodModel).where(
                PricePeriodModel.site_id == site_id,
                PricePeriodModel.period_start < cutoff,
            )
        )
        return result.rowcount or 0


class PriceEngineStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, site_id: int) -> PriceEngineStatus | None:
        row = await self._session.get(PriceEngineStateModel, site_id)
        if row is None:
            return None
        return PriceEngineStatus(
            site_id=row.site_id,
            last_market_refresh_at=row.last_market_refresh_at,
            last_import_refresh_at=row.last_import_refresh_at,
            last_export_refresh_at=row.last_export_refresh_at,
            last_error=row.last_error,
            missing_periods_count=row.missing_periods_count,
            data_age_seconds=row.data_age_seconds,
            optimization_mode=OptimizationMode(row.optimization_mode),
        )

    async def upsert(
        self,
        *,
        site_id: int,
        last_market_refresh_at: datetime | None = None,
        last_import_refresh_at: datetime | None = None,
        last_export_refresh_at: datetime | None = None,
        last_error: str | None = None,
        missing_periods_count: int = 0,
        data_age_seconds: int | None = None,
        optimization_mode: OptimizationMode = OptimizationMode.MONITOR_ONLY,
    ) -> None:
        row = await self._session.get(PriceEngineStateModel, site_id)
        if row is None:
            row = PriceEngineStateModel(
                site_id=site_id,
                optimization_mode=optimization_mode.value,
            )
            self._session.add(row)
        if last_market_refresh_at is not None:
            row.last_market_refresh_at = last_market_refresh_at
        if last_import_refresh_at is not None:
            row.last_import_refresh_at = last_import_refresh_at
        if last_export_refresh_at is not None:
            row.last_export_refresh_at = last_export_refresh_at
        row.last_error = last_error
        row.missing_periods_count = missing_periods_count
        row.data_age_seconds = data_age_seconds
        row.optimization_mode = optimization_mode.value
        await self._session.flush()
