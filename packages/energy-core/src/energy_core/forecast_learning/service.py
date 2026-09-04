"""Forecast learning orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.price_period_repo import PricePeriodRepository
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.db.solar_forecast_repo import SolarForecastRepository
from energy_core.flexible_load.house_load import HouseLoadForecastProvider
from energy_core.forecast_learning.metrics import compute_metric_summary
from energy_core.forecast_learning.repo import ForecastSnapshotRepository
from energy_core.forecast_learning.types import ForecastKind, ForecastLearningSummary, ForecastSnapshot
from energy_core.price_engine.periods import current_period_start


class ForecastLearningService:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite
        self._repo = ForecastSnapshotRepository(session, is_sqlite=is_sqlite)
        self._price_repo = PricePeriodRepository(session, is_sqlite=is_sqlite)
        self._reading_repo = EnergyReadingRepository(session, is_sqlite)
        self._solar_repo = SolarForecastRepository(session)
        self._load_provider = HouseLoadForecastProvider()

    async def record_price_predictions(self, site_id: int, *, timezone: str, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        period_start = current_period_start(timezone=timezone, now=now)
        end = period_start + timedelta(days=2)
        periods = await self._price_repo.list_range(site_id, start=period_start, end=end)
        count = 0
        for period in periods:
            if period.import_price_sek_kwh is None:
                continue
            inserted = await self._repo.insert_prediction_if_missing(
                site_id=site_id,
                period_start=period.period_start,
                period_end=period.period_end,
                kind=ForecastKind.IMPORT_PRICE_SEK_KWH,
                predicted_value=period.import_price_sek_kwh,
                forecast_recorded_at=now,
                model_version="price-engine-v1",
            )
            if inserted:
                count += 1
        return count

    async def record_load_predictions(self, site_id: int, *, timezone: str, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        period_start = current_period_start(timezone=timezone, now=now)
        end = period_start + timedelta(hours=24)
        lookback = now - timedelta(days=14)
        readings = await self._reading_repo.list_readings(site_id, from_time=lookback, to_time=now, limit=5000)
        tuples = [(r.recorded_at, r.solar_production_w, r.consumption_w) for r in readings]
        series = self._load_provider.forecast_series(
            tuples,
            timezone=timezone,
            start=period_start,
            end=end,
            interval_minutes=15,
        )
        count = 0
        for point in series.points:
            if point.timestamp < period_start:
                continue
            await self._repo.upsert_prediction(
                site_id=site_id,
                period_start=point.timestamp,
                period_end=point.timestamp + timedelta(minutes=15),
                kind=ForecastKind.LOAD_W,
                predicted_value=point.expected_power_w,
                forecast_recorded_at=now,
                model_version=series.source,
            )
            count += 1
        return count

    async def record_solar_predictions(self, site_id: int, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        forecast = await self._solar_repo.get_latest(site_id)
        if forecast is None:
            return 0
        count = 0
        for point in forecast.points:
            if point.timestamp < now:
                continue
            await self._repo.upsert_prediction(
                site_id=site_id,
                period_start=point.timestamp,
                period_end=point.timestamp + timedelta(minutes=15),
                kind=ForecastKind.SOLAR_W,
                predicted_value=point.corrected_power_w,
                forecast_recorded_at=now,
                model_version=forecast.model_version,
            )
            count += 1
        return count

    async def reconcile_actuals(self, site_id: int, *, timezone: str, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        pending = await self._repo.list_pending_actuals(site_id, period_end_before=now)
        count = 0
        for snap in pending:
            actual = await self._actual_for_snapshot(site_id, snap)
            if actual is None:
                continue
            if await self._repo.set_actual(
                site_id=site_id,
                period_start=snap.period_start,
                kind=snap.kind,
                actual_value=actual,
                actual_recorded_at=now,
            ):
                count += 1
        return count

    async def sync_site(self, site_id: int, *, timezone: str, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        return {
            "price_predictions": await self.record_price_predictions(site_id, timezone=timezone, now=now),
            "load_predictions": await self.record_load_predictions(site_id, timezone=timezone, now=now),
            "solar_predictions": await self.record_solar_predictions(site_id, now=now),
            "actuals_reconciled": await self.reconcile_actuals(site_id, timezone=timezone, now=now),
        }

    async def summary(self, site_id: int, *, days: int = 30) -> ForecastLearningSummary:
        now = datetime.now(UTC)
        start = now - timedelta(days=days)
        snapshots = await self._repo.list_range(site_id, start=start, end=now, reconciled_only=True)
        metrics = tuple(
            compute_metric_summary(kind, snapshots)
            for kind in ForecastKind
        )
        last_reconciled = max(
            (s.actual_recorded_at for s in snapshots if s.actual_recorded_at is not None),
            default=None,
        )
        return ForecastLearningSummary(
            site_id=site_id,
            days=days,
            metrics=metrics,
            last_reconciled_at=last_reconciled,
        )

    async def recent(
        self,
        site_id: int,
        *,
        kind: ForecastKind | None = None,
        days: int = 7,
        limit: int = 48,
    ) -> tuple[ForecastSnapshot, ...]:
        now = datetime.now(UTC)
        start = now - timedelta(days=days)
        snapshots = await self._repo.list_range(
            site_id,
            start=start,
            end=now,
            kind=kind,
            reconciled_only=True,
        )
        return snapshots[:limit]

    async def _actual_for_snapshot(self, site_id: int, snap: ForecastSnapshot) -> float | None:
        if snap.kind == ForecastKind.IMPORT_PRICE_SEK_KWH:
            period = await self._price_repo.get_at(site_id, snap.period_start)
            if period is None or period.import_price_sek_kwh is None:
                return None
            return period.import_price_sek_kwh

        readings = await self._reading_repo.list_readings(
            site_id,
            from_time=snap.period_start,
            to_time=snap.period_end,
            limit=200,
        )
        if not readings:
            return None
        if snap.kind == ForecastKind.LOAD_W:
            values = [r.consumption_w for r in readings if r.consumption_w is not None]
        else:
            values = [r.solar_production_w for r in readings if r.solar_production_w is not None]
        if not values:
            return None
        return sum(values) / len(values)
