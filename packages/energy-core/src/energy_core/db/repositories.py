from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    EnergyReadingModel,
    HistoricalMonthlyEnergyModel,
    MarketPriceModel,
    SiteModel,
)
from energy_core.domain import NormalizedEnergyReading


@dataclass(frozen=True, slots=True)
class SiteWithLatestReading:
    id: int
    slug: str
    name: str
    timezone: str
    external_system_id: str | None
    fallback_purchase_price_sek_kwh: float
    export_compensation_sek_kwh: float
    latest_reading: "ReadingRecord | None"
    main_fuse_a: float | None = None
    safety_margin_a: float = 2.0


@dataclass(frozen=True, slots=True)
class ReadingRecord:
    site_id: int
    site_slug: str
    recorded_at: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float


@dataclass(frozen=True, slots=True)
class AggregatedReading:
    bucket_start: datetime
    solar_production_w: float
    consumption_w: float
    grid_import_w: float
    grid_export_w: float
    battery_soc_pct: float
    battery_power_w: float


PeakPeriod = Literal["day", "month", "year"]


@dataclass(frozen=True, slots=True)
class PeakReading:
    period_start: str
    solar_production_w: float
    battery_charge_w: float
    battery_discharge_w: float


@dataclass(frozen=True, slots=True)
class FinancialStat:
    period_start: str
    solar_self_consumed_kwh: float
    battery_self_consumed_kwh: float
    exported_kwh: float
    imported_kwh: float
    solar_savings_sek: float
    battery_savings_sek: float
    export_revenue_sek: float
    grid_import_cost_sek: float
    market_priced_fraction: float


@dataclass(frozen=True, slots=True)
class HistoricalMonthlyEnergy:
    year: int
    month: int
    imported_kwh: float
    imported_cost_sek: float | None
    source: str
    estimated: bool


def _floor_bucket(ts: datetime, bucket_minutes: int) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    minute = (ts.minute // bucket_minutes) * bucket_minutes
    return ts.replace(minute=minute, second=0, microsecond=0)


def _bucket_readings_in_python(
    readings: list[ReadingRecord],
    bucket_minutes: int,
) -> list[AggregatedReading]:
    buckets: dict[datetime, list[ReadingRecord]] = defaultdict(list)
    for reading in readings:
        buckets[_floor_bucket(reading.recorded_at, bucket_minutes)].append(reading)

    result: list[AggregatedReading] = []
    for bucket_start in sorted(buckets):
        group = buckets[bucket_start]
        count = len(group)
        result.append(
            AggregatedReading(
                bucket_start=bucket_start,
                solar_production_w=sum(r.solar_production_w for r in group) / count,
                consumption_w=sum(r.consumption_w for r in group) / count,
                grid_import_w=sum(r.grid_import_w for r in group) / count,
                grid_export_w=sum(r.grid_export_w for r in group) / count,
                battery_soc_pct=sum(r.battery_soc_pct for r in group) / count,
                battery_power_w=sum(r.battery_power_w for r in group) / count,
            )
        )
    return result


class SiteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[SiteModel]:
        result = await self._session.scalars(select(SiteModel).order_by(SiteModel.name))
        return list(result)

    async def get_by_slug(self, slug: str) -> SiteModel | None:
        return await self._session.scalar(select(SiteModel).where(SiteModel.slug == slug))

    async def upsert_site(
        self,
        slug: str,
        name: str,
        timezone: str,
        external_system_id: str | None = None,
        fallback_purchase_price_sek_kwh: float | None = None,
        export_compensation_sek_kwh: float | None = None,
        main_fuse_a: float | None = None,
        safety_margin_a: float | None = None,
    ) -> SiteModel:
        existing = await self.get_by_slug(slug)
        if existing:
            existing.name = name
            existing.timezone = timezone
            if external_system_id is not None:
                existing.external_system_id = external_system_id
            if fallback_purchase_price_sek_kwh is not None:
                existing.fallback_purchase_price_sek_kwh = fallback_purchase_price_sek_kwh
            if export_compensation_sek_kwh is not None:
                existing.export_compensation_sek_kwh = export_compensation_sek_kwh
            if main_fuse_a is not None:
                existing.main_fuse_a = main_fuse_a
            if safety_margin_a is not None:
                existing.safety_margin_a = safety_margin_a
            await self._session.flush()
            return existing
        site = SiteModel(
            slug=slug,
            name=name,
            timezone=timezone,
            external_system_id=external_system_id,
            fallback_purchase_price_sek_kwh=(
                fallback_purchase_price_sek_kwh
                if fallback_purchase_price_sek_kwh is not None
                else 2.0
            ),
            export_compensation_sek_kwh=(
                export_compensation_sek_kwh if export_compensation_sek_kwh is not None else 0.8
            ),
        )
        self._session.add(site)
        await self._session.flush()
        return site

    async def create_site(
        self,
        slug: str,
        name: str,
        timezone: str,
        external_system_id: str | None = None,
        fallback_purchase_price_sek_kwh: float | None = None,
        export_compensation_sek_kwh: float | None = None,
        main_fuse_a: float | None = None,
        safety_margin_a: float | None = None,
    ) -> SiteModel:
        if await self.get_by_slug(slug):
            raise ValueError(f"Site slug already exists: {slug}")
        return await self.upsert_site(
            slug,
            name,
            timezone,
            external_system_id,
            fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh,
            main_fuse_a,
            safety_margin_a,
        )

    async def update_site(
        self,
        slug: str,
        *,
        name: str | None = None,
        timezone: str | None = None,
        external_system_id: str | None = None,
        fallback_purchase_price_sek_kwh: float | None = None,
        export_compensation_sek_kwh: float | None = None,
        main_fuse_a: float | None = None,
        safety_margin_a: float | None = None,
    ) -> SiteModel:
        site = await self.get_by_slug(slug)
        if site is None:
            raise KeyError(slug)
        if name is not None:
            site.name = name.strip()
        if timezone is not None:
            site.timezone = timezone.strip()
        if external_system_id is not None:
            site.external_system_id = external_system_id.strip() or None
        if fallback_purchase_price_sek_kwh is not None:
            site.fallback_purchase_price_sek_kwh = fallback_purchase_price_sek_kwh
        if export_compensation_sek_kwh is not None:
            site.export_compensation_sek_kwh = export_compensation_sek_kwh
        if main_fuse_a is not None:
            site.main_fuse_a = main_fuse_a
        if safety_margin_a is not None:
            site.safety_margin_a = safety_margin_a
        await self._session.flush()
        return site

    async def delete_site(self, slug: str) -> None:
        site = await self.get_by_slug(slug)
        if site is None:
            raise KeyError(slug)
        await self._session.delete(site)


@dataclass(frozen=True, slots=True)
class MarketPriceRecord:
    site_id: int
    recorded_at: datetime
    spot_price_sek_kwh: float
    all_in_price_sek_kwh: float | None


class MarketPriceRepository:
    def __init__(self, session: AsyncSession, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert_prices(
        self,
        site_id: int,
        prices: list[tuple[datetime, float, float | None]],
    ) -> None:
        for recorded_at, spot_price, all_in_price in prices:
            values = {
                "site_id": site_id,
                "recorded_at": recorded_at,
                "spot_price_sek_kwh": spot_price,
                "all_in_price_sek_kwh": all_in_price,
            }
            insert = sqlite_insert if self._is_sqlite else pg_insert
            stmt = insert(MarketPriceModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "recorded_at"],
                set_={
                    "spot_price_sek_kwh": stmt.excluded.spot_price_sek_kwh,
                    "all_in_price_sek_kwh": stmt.excluded.all_in_price_sek_kwh,
                },
            )
            await self._session.execute(stmt)

    async def has_price_at(self, site_id: int, recorded_at: datetime) -> bool:
        value = await self._session.scalar(
            select(MarketPriceModel.site_id).where(
                MarketPriceModel.site_id == site_id,
                MarketPriceModel.recorded_at == recorded_at,
            )
        )
        return value is not None

    async def get_at(self, site_id: int, recorded_at: datetime) -> MarketPriceRecord | None:
        row = await self._session.scalar(
            select(MarketPriceModel).where(
                MarketPriceModel.site_id == site_id,
                MarketPriceModel.recorded_at == recorded_at,
            )
        )
        if row is None:
            return None
        return MarketPriceRecord(
            site_id=row.site_id,
            recorded_at=row.recorded_at,
            spot_price_sek_kwh=row.spot_price_sek_kwh,
            all_in_price_sek_kwh=row.all_in_price_sek_kwh,
        )


class HistoricalEnergyRepository:
    def __init__(self, session: AsyncSession, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert_months(
        self,
        site_id: int,
        months: list[HistoricalMonthlyEnergy],
    ) -> None:
        insert = sqlite_insert if self._is_sqlite else pg_insert
        for month in months:
            stmt = insert(HistoricalMonthlyEnergyModel).values(
                site_id=site_id,
                year=month.year,
                month=month.month,
                imported_kwh=month.imported_kwh,
                imported_cost_sek=month.imported_cost_sek,
                source=month.source,
                estimated=month.estimated,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "year", "month"],
                set_={
                    "imported_kwh": stmt.excluded.imported_kwh,
                    "imported_cost_sek": stmt.excluded.imported_cost_sek,
                    "source": stmt.excluded.source,
                    "estimated": stmt.excluded.estimated,
                },
            )
            await self._session.execute(stmt)

    async def list_for_site(self, site_id: int) -> list[HistoricalMonthlyEnergy]:
        rows = (
            await self._session.execute(
                select(HistoricalMonthlyEnergyModel)
                .where(HistoricalMonthlyEnergyModel.site_id == site_id)
                .order_by(
                    HistoricalMonthlyEnergyModel.year,
                    HistoricalMonthlyEnergyModel.month,
                )
            )
        ).scalars()
        return [
            HistoricalMonthlyEnergy(
                year=row.year,
                month=row.month,
                imported_kwh=row.imported_kwh,
                imported_cost_sek=row.imported_cost_sek,
                source=row.source,
                estimated=row.estimated,
            )
            for row in rows
        ]


class EnergyReadingRepository:
    def __init__(self, session: AsyncSession, is_sqlite: bool) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def upsert_reading(self, site_id: int, reading: NormalizedEnergyReading) -> None:
        values = {
            "site_id": site_id,
            "recorded_at": reading.recorded_at,
            "solar_production_w": reading.solar_production_w,
            "consumption_w": reading.consumption_w,
            "grid_import_w": reading.grid_import_w,
            "grid_export_w": reading.grid_export_w,
            "battery_soc_pct": reading.battery_soc_pct,
            "battery_power_w": reading.battery_power_w,
            "ev_power_w": reading.ev_power_w,
            "battery_charge_w": reading.battery_charge_w,
            "battery_discharge_w": reading.battery_discharge_w,
        }
        update_fields = {
            "solar_production_w": "solar_production_w",
            "consumption_w": "consumption_w",
            "grid_import_w": "grid_import_w",
            "grid_export_w": "grid_export_w",
            "battery_soc_pct": "battery_soc_pct",
            "battery_power_w": "battery_power_w",
            "ev_power_w": "ev_power_w",
            "battery_charge_w": "battery_charge_w",
            "battery_discharge_w": "battery_discharge_w",
        }
        if self._is_sqlite:
            stmt = sqlite_insert(EnergyReadingModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "recorded_at"],
                set_={key: getattr(stmt.excluded, key) for key in update_fields},
            )
        else:
            stmt = pg_insert(EnergyReadingModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["site_id", "recorded_at"],
                set_={key: getattr(stmt.excluded, key) for key in update_fields},
            )
        await self._session.execute(stmt)

    async def get_latest_for_site(self, site_id: int) -> ReadingRecord | None:
        stmt = (
            select(EnergyReadingModel, SiteModel.slug)
            .join(SiteModel, SiteModel.id == EnergyReadingModel.site_id)
            .where(EnergyReadingModel.site_id == site_id)
            .order_by(EnergyReadingModel.recorded_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        reading, slug = row
        return self._to_record(reading, slug)

    async def list_sites_with_latest(self) -> list[SiteWithLatestReading]:
        sites = await self._session.scalars(select(SiteModel).order_by(SiteModel.name))
        result: list[SiteWithLatestReading] = []
        for site in sites:
            latest = await self.get_latest_for_site(site.id)
            result.append(
                SiteWithLatestReading(
                    id=site.id,
                    slug=site.slug,
                    name=site.name,
                    timezone=site.timezone,
                    external_system_id=site.external_system_id,
                    fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
                    export_compensation_sek_kwh=site.export_compensation_sek_kwh,
                    main_fuse_a=site.main_fuse_a,
                    safety_margin_a=site.safety_margin_a,
                    latest_reading=latest,
                )
            )
        return result

    async def list_readings(
        self,
        site_id: int,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[ReadingRecord]:
        stmt = (
            select(EnergyReadingModel, SiteModel.slug)
            .join(SiteModel, SiteModel.id == EnergyReadingModel.site_id)
            .where(EnergyReadingModel.site_id == site_id)
        )
        if from_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at >= from_time)
        if to_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at <= to_time)
        stmt = stmt.order_by(EnergyReadingModel.recorded_at.asc()).limit(limit)
        rows = (await self._session.execute(stmt)).all()
        return [self._to_record(reading, slug) for reading, slug in rows]

    async def list_aggregated(
        self,
        site_id: int,
        bucket_minutes: int,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[AggregatedReading]:
        """Time-bucket aggregation. Uses SQL on PostgreSQL, Python bucketing on SQLite."""
        if self._is_sqlite:
            readings = await self.list_readings(site_id, from_time, to_time, limit=10000)
            return _bucket_readings_in_python(readings, bucket_minutes)

        if bucket_minutes >= 60 and bucket_minutes % 60 == 0:
            bucket_expr = func.date_trunc("hour", EnergyReadingModel.recorded_at)
        else:
            bucket_expr = func.date_trunc("minute", EnergyReadingModel.recorded_at)
        stmt = (
            select(
                bucket_expr.label("bucket_start"),
                func.avg(EnergyReadingModel.solar_production_w).label("solar_production_w"),
                func.avg(EnergyReadingModel.consumption_w).label("consumption_w"),
                func.avg(EnergyReadingModel.grid_import_w).label("grid_import_w"),
                func.avg(EnergyReadingModel.grid_export_w).label("grid_export_w"),
                func.avg(EnergyReadingModel.battery_soc_pct).label("battery_soc_pct"),
                func.avg(EnergyReadingModel.battery_power_w).label("battery_power_w"),
            )
            .where(EnergyReadingModel.site_id == site_id)
            .group_by(bucket_expr)
            .order_by(bucket_expr)
        )
        if from_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at >= from_time)
        if to_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at <= to_time)

        rows = (await self._session.execute(stmt)).all()
        return [
            AggregatedReading(
                bucket_start=row.bucket_start,
                solar_production_w=float(row.solar_production_w or 0),
                consumption_w=float(row.consumption_w or 0),
                grid_import_w=float(row.grid_import_w or 0),
                grid_export_w=float(row.grid_export_w or 0),
                battery_soc_pct=float(row.battery_soc_pct or 0),
                battery_power_w=float(row.battery_power_w or 0),
            )
            for row in rows
        ]

    async def list_peaks(
        self,
        site_id: int,
        period: PeakPeriod,
        timezone: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[PeakReading]:
        """Return maximum solar, battery charge and battery discharge per local period."""
        if self._is_sqlite:
            stmt = select(
                EnergyReadingModel.recorded_at,
                EnergyReadingModel.solar_production_w,
                EnergyReadingModel.battery_power_w,
            ).where(EnergyReadingModel.site_id == site_id)
            if from_time is not None:
                stmt = stmt.where(EnergyReadingModel.recorded_at >= from_time)
            if to_time is not None:
                stmt = stmt.where(EnergyReadingModel.recorded_at < to_time)
            stmt = stmt.order_by(EnergyReadingModel.recorded_at)
            rows = (await self._session.execute(stmt)).all()
            zone = ZoneInfo(timezone)
            peaks: dict[str, tuple[float, float, float]] = {}
            for row in rows:
                recorded_at = row.recorded_at
                if recorded_at.tzinfo is None:
                    recorded_at = recorded_at.replace(tzinfo=UTC)
                local_time = recorded_at.astimezone(zone)
                if period == "day":
                    key = local_time.strftime("%Y-%m-%d")
                elif period == "month":
                    key = local_time.strftime("%Y-%m")
                else:
                    key = local_time.strftime("%Y")
                solar, charge, discharge = peaks.get(key, (0.0, 0.0, 0.0))
                battery_power = float(row.battery_power_w or 0.0)
                peaks[key] = (
                    max(solar, float(row.solar_production_w or 0.0)),
                    max(charge, battery_power),
                    max(discharge, -battery_power),
                )
            return [
                PeakReading(
                    period_start=key,
                    solar_production_w=values[0],
                    battery_charge_w=values[1],
                    battery_discharge_w=values[2],
                )
                for key, values in sorted(peaks.items())
            ]

        local_time = func.timezone(timezone, EnergyReadingModel.recorded_at)
        bucket_expr = func.date_trunc(period, local_time)
        stmt = (
            select(
                bucket_expr.label("period_start"),
                func.max(EnergyReadingModel.solar_production_w).label("solar_production_w"),
                func.max(EnergyReadingModel.battery_power_w).label("battery_charge_w"),
                func.min(EnergyReadingModel.battery_power_w).label("battery_discharge_w"),
            )
            .where(EnergyReadingModel.site_id == site_id)
            .group_by(bucket_expr)
            .order_by(bucket_expr)
        )
        if from_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at >= from_time)
        if to_time is not None:
            stmt = stmt.where(EnergyReadingModel.recorded_at < to_time)
        rows = (await self._session.execute(stmt)).all()
        period_format = {"day": "%Y-%m-%d", "month": "%Y-%m", "year": "%Y"}[period]
        return [
            PeakReading(
                period_start=row.period_start.strftime(period_format),
                solar_production_w=max(0.0, float(row.solar_production_w or 0.0)),
                battery_charge_w=max(0.0, float(row.battery_charge_w or 0.0)),
                battery_discharge_w=max(0.0, -float(row.battery_discharge_w or 0.0)),
            )
            for row in rows
        ]

    async def list_financial_stats(
        self,
        site_id: int,
        period: PeakPeriod,
        timezone: str,
        fallback_purchase_price_sek_kwh: float,
        export_compensation_sek_kwh: float,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[FinancialStat]:
        reading_stmt = select(
            EnergyReadingModel.recorded_at,
            EnergyReadingModel.solar_production_w,
            EnergyReadingModel.consumption_w,
            EnergyReadingModel.grid_import_w,
            EnergyReadingModel.grid_export_w,
            EnergyReadingModel.battery_power_w,
        ).where(EnergyReadingModel.site_id == site_id)
        if from_time is not None:
            reading_stmt = reading_stmt.where(EnergyReadingModel.recorded_at >= from_time)
        if to_time is not None:
            reading_stmt = reading_stmt.where(EnergyReadingModel.recorded_at < to_time)
        reading_stmt = reading_stmt.order_by(EnergyReadingModel.recorded_at)
        readings = (await self._session.execute(reading_stmt)).all()
        if len(readings) < 2:
            return []

        price_stmt = select(
            MarketPriceModel.recorded_at,
            MarketPriceModel.all_in_price_sek_kwh,
        ).where(MarketPriceModel.site_id == site_id)
        if from_time is not None:
            price_stmt = price_stmt.where(MarketPriceModel.recorded_at >= from_time)
        if to_time is not None:
            price_stmt = price_stmt.where(MarketPriceModel.recorded_at < to_time)
        price_rows = (await self._session.execute(price_stmt)).all()
        prices: dict[datetime, float] = {}
        for row in price_rows:
            timestamp = row.recorded_at
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            if row.all_in_price_sek_kwh is not None:
                prices[timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)] = float(
                    row.all_in_price_sek_kwh
                )

        zone = ZoneInfo(timezone)
        totals: dict[str, list[float]] = {}
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
            local_time = started_at.astimezone(zone)
            if period == "day":
                key = local_time.strftime("%Y-%m-%d")
            elif period == "month":
                key = local_time.strftime("%Y-%m")
            else:
                key = local_time.strftime("%Y")

            solar_w = max(0.0, float(previous.solar_production_w or 0.0))
            consumption_w = max(0.0, float(previous.consumption_w or 0.0))
            discharge_w = max(0.0, -float(previous.battery_power_w or 0.0))
            imported_w = max(0.0, float(previous.grid_import_w or 0.0))
            exported_w = max(0.0, float(previous.grid_export_w or 0.0))
            solar_self_w = min(solar_w, max(0.0, consumption_w - discharge_w - imported_w))
            battery_self_w = min(discharge_w, max(0.0, consumption_w - solar_self_w))
            solar_kwh = solar_self_w * hours / 1000.0
            battery_kwh = battery_self_w * hours / 1000.0
            export_kwh = exported_w * hours / 1000.0
            import_kwh = imported_w * hours / 1000.0

            price_key = started_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            market_price = prices.get(price_key)
            purchase_price = (
                market_price if market_price is not None else fallback_purchase_price_sek_kwh
            )
            values = totals.setdefault(key, [0.0] * 10)
            values[0] += solar_kwh
            values[1] += battery_kwh
            values[2] += export_kwh
            values[3] += import_kwh
            values[4] += solar_kwh * purchase_price
            values[5] += battery_kwh * purchase_price
            values[6] += export_kwh * export_compensation_sek_kwh
            values[7] += import_kwh * purchase_price
            values[8] += solar_kwh + battery_kwh + import_kwh
            if market_price is not None:
                values[9] += solar_kwh + battery_kwh + import_kwh

        return [
            FinancialStat(
                period_start=key,
                solar_self_consumed_kwh=round(values[0], 3),
                battery_self_consumed_kwh=round(values[1], 3),
                exported_kwh=round(values[2], 3),
                imported_kwh=round(values[3], 3),
                solar_savings_sek=round(values[4], 2),
                battery_savings_sek=round(values[5], 2),
                export_revenue_sek=round(values[6], 2),
                grid_import_cost_sek=round(values[7], 2),
                market_priced_fraction=round(values[9] / values[8], 3) if values[8] > 0 else 0.0,
            )
            for key, values in sorted(totals.items())
        ]

    @staticmethod
    def _to_record(reading: EnergyReadingModel, slug: str) -> ReadingRecord:
        return ReadingRecord(
            site_id=reading.site_id,
            site_slug=slug,
            recorded_at=reading.recorded_at,
            solar_production_w=reading.solar_production_w,
            consumption_w=reading.consumption_w,
            grid_import_w=reading.grid_import_w,
            grid_export_w=reading.grid_export_w,
            battery_soc_pct=reading.battery_soc_pct,
            battery_power_w=reading.battery_power_w,
        )
