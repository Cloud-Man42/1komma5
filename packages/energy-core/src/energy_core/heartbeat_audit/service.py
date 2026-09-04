"""Heartbeat audit service — snapshots and cost rollups."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.charging.savings import compute_charging_savings
from energy_core.db.ev_bridge_cycle_repo import EvBridgeCycleRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel, VirtualChargerDecisionModel
from energy_core.db.price_period_repo import PricePeriodRepository
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.energy_optimizer.types import EovConfig
from energy_core.heartbeat_audit.period_snapshots import build_period_snapshots
from energy_core.heartbeat_audit.rollup import aggregate_monthly_rollups, build_daily_rollup
from energy_core.heartbeat_audit.types import AuditPeriodSnapshot, DailyAuditRollup, MonthlyAuditRollup
from energy_core.price_engine.periods import local_day_bounds, local_today
from energy_core.price_engine.types import OptimizationMode


class HeartbeatAuditService:
    def __init__(self, session: AsyncSession, *, is_sqlite: bool = False) -> None:
        self._session = session
        self._is_sqlite = is_sqlite

    async def today(
        self,
        *,
        site_id: int,
        site_slug: str,
        timezone: str,
        fallback_purchase_price_sek_kwh: float,
        export_compensation_sek_kwh: float,
        optimization_mode: OptimizationMode = OptimizationMode.MONITOR_ONLY,
    ) -> tuple[DailyAuditRollup | None, tuple[AuditPeriodSnapshot, ...]]:
        day = local_today(timezone)
        return await self._day_audit(
            site_id=site_id,
            site_slug=site_slug,
            timezone=timezone,
            day=day,
            fallback_purchase_price_sek_kwh=fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=export_compensation_sek_kwh,
            optimization_mode=optimization_mode,
        )

    async def month(
        self,
        *,
        site_id: int,
        site_slug: str,
        timezone: str,
        fallback_purchase_price_sek_kwh: float,
        export_compensation_sek_kwh: float,
        month: str | None = None,
    ) -> tuple[MonthlyAuditRollup | None, tuple[DailyAuditRollup, ...]]:
        ref = local_today(timezone)
        if month:
            year, mon = int(month[:4]), int(month[5:7])
            ref = date(year, mon, 1)
        start_day = ref.replace(day=1)
        if start_day.month == 12:
            end_day = date(start_day.year + 1, 1, 1)
        else:
            end_day = date(start_day.year, start_day.month + 1, 1)

        daily_rollups: list[DailyAuditRollup] = []
        cursor = start_day
        while cursor < end_day and cursor <= local_today(timezone):
            rollup, _ = await self._day_audit(
                site_id=site_id,
                site_slug=site_slug,
                timezone=timezone,
                day=cursor,
                fallback_purchase_price_sek_kwh=fallback_purchase_price_sek_kwh,
                export_compensation_sek_kwh=export_compensation_sek_kwh,
                include_snapshots=False,
            )
            if rollup is not None:
                daily_rollups.append(rollup)
            cursor += timedelta(days=1)

        return aggregate_monthly_rollups(tuple(daily_rollups)), tuple(daily_rollups)

    async def _day_audit(
        self,
        *,
        site_id: int,
        site_slug: str,
        timezone: str,
        day: date,
        fallback_purchase_price_sek_kwh: float,
        export_compensation_sek_kwh: float,
        optimization_mode: OptimizationMode = OptimizationMode.MONITOR_ONLY,
        include_snapshots: bool = True,
    ) -> tuple[DailyAuditRollup | None, tuple[AuditPeriodSnapshot, ...]]:
        start_utc, end_utc = local_day_bounds(day, timezone)
        period_repo = PricePeriodRepository(self._session, is_sqlite=self._is_sqlite)
        periods = await period_repo.list_range(site_id, start=start_utc, end=end_utc)
        if not periods:
            return None, ()

        reading_repo = EnergyReadingRepository(self._session, is_sqlite=self._is_sqlite)
        stats = await reading_repo.list_financial_stats(
            site_id,
            period="day",
            timezone=timezone,
            fallback_purchase_price_sek_kwh=fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=export_compensation_sek_kwh,
            from_time=start_utc,
            to_time=end_utc,
        )
        if not stats:
            return None, ()

        financial = stats[0]
        ev_savings = await self._ev_savings_for_day(site_id, start_utc, end_utc)
        rollup = build_daily_rollup(
            day=financial.period_start,
            financial=financial,
            horizon=periods,
            ev_savings_sek=ev_savings,
            eov_config=EovConfig(),
        )

        snapshots: tuple[AuditPeriodSnapshot, ...] = ()
        if include_snapshots:
            readings = await self._readings_for_range(site_id, start_utc, end_utc)
            decisions = await self._decisions_for_range(site_id, start_utc, end_utc)
            snapshots = build_period_snapshots(
                site_slug=site_slug,
                timezone=timezone,
                periods=periods,
                readings=readings,
                decisions=decisions,
                optimization_mode=optimization_mode,
            )

        return rollup, snapshots

    async def _readings_for_range(
        self,
        site_id: int,
        start: datetime,
        end: datetime,
    ) -> tuple[tuple[datetime, dict[str, float | None]], ...]:
        rows = await self._session.scalars(
            select(EnergyReadingModel)
            .where(
                EnergyReadingModel.site_id == site_id,
                EnergyReadingModel.recorded_at >= start,
                EnergyReadingModel.recorded_at < end,
            )
            .order_by(EnergyReadingModel.recorded_at.asc())
        )
        return tuple(
            (
                row.recorded_at,
                {
                    "grid_import_w": row.grid_import_w,
                    "grid_export_w": row.grid_export_w,
                    "battery_soc_pct": row.battery_soc_pct,
                    "ev_power_w": row.ev_power_w,
                },
            )
            for row in rows.all()
        )

    async def _decisions_for_range(
        self,
        site_id: int,
        start: datetime,
        end: datetime,
    ) -> tuple[tuple[datetime, dict[str, str | None]], ...]:
        rows = await self._session.scalars(
            select(VirtualChargerDecisionModel)
            .where(
                VirtualChargerDecisionModel.site_id == site_id,
                VirtualChargerDecisionModel.recorded_at >= start,
                VirtualChargerDecisionModel.recorded_at < end,
            )
            .order_by(VirtualChargerDecisionModel.recorded_at.asc())
        )
        return tuple(
            (
                row.recorded_at,
                {
                    "heartbeat_mode": row.heartbeat_mode,
                    "ai_decision": row.ai_decision,
                    "reason": row.reason,
                },
            )
            for row in rows.all()
        )

    async def _ev_savings_for_day(self, site_id: int, start: datetime, end: datetime) -> float:
        charger_repo = EvChargerRepository(self._session)
        cycle_repo = EvBridgeCycleRepository(self._session)
        total = 0.0
        for charger in await charger_repo.list_for_site(site_id):
            cycles = await cycle_repo.list_for_charger(
                charger.id,
                from_time=start,
                to_time=end,
            )
            if len(cycles) < 2:
                continue
            savings = compute_charging_savings(
                cycles,
                phases=charger.phases,
                nominal_voltage_v=charger.nominal_voltage_v,
            )
            total += savings.savings_sek
        return round(total, 2)
