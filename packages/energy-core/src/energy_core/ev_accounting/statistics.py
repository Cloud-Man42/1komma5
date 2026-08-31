"""Aggregate EV charging statistics over periods."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from energy_core.db.ev_session_repo import EvChargingSessionRecord, EvChargingSessionRepository

Period = Literal["session", "day", "week", "month", "year", "all"]


@dataclass(frozen=True, slots=True)
class EVStatsResult:
    period: str
    period_from: datetime
    period_to: datetime
    total_energy_kwh: float
    actual_cost_sek: float
    reference_cost_sek: float | None
    savings_sek: float | None
    average_cost_sek_per_kwh: float | None
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float
    renewable_share_percent: float
    grid_share_percent: float
    smart_charging_savings_sek: float | None
    solar_contribution_sek: float
    session_count: int


class EVStatisticsService:
    def __init__(self, repo: EvChargingSessionRepository) -> None:
        self._repo = repo

    async def stats(
        self,
        charger_id: int,
        *,
        period: Period = "month",
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> EVStatsResult:
        now = datetime.now(UTC)
        period_to = to_time or now
        period_from = from_time or self._default_from(period, period_to)

        # ACTIVE belongs here: the sampler keeps a running session's totals up to
        # date, and leaving it out made a day of charging show as 0 kWh until the
        # car was unplugged.
        sessions = await self._repo.list_for_charger(
            charger_id,
            from_time=period_from,
            to_time=period_to,
            statuses=("COMPLETED", "ESTIMATED", "INCOMPLETE", "ACTIVE"),
        )
        return self._aggregate(sessions, period=period, period_from=period_from, period_to=period_to)

    @staticmethod
    def _default_from(period: Period, to_time: datetime) -> datetime:
        if period == "day":
            return to_time - timedelta(days=1)
        if period == "week":
            return to_time - timedelta(days=7)
        if period == "month":
            return to_time - timedelta(days=30)
        if period == "year":
            return to_time - timedelta(days=365)
        if period == "all":
            return datetime(2000, 1, 1, tzinfo=UTC)
        return to_time - timedelta(days=30)

    @staticmethod
    def _aggregate(
        sessions: list[EvChargingSessionRecord],
        *,
        period: str,
        period_from: datetime,
        period_to: datetime,
    ) -> EVStatsResult:
        total_energy = sum(s.total_energy_kwh or 0 for s in sessions)
        actual_cost = sum(s.actual_cost_sek or 0 for s in sessions)
        refs = [s.reference_cost_sek for s in sessions if s.reference_cost_sek is not None]
        reference = sum(refs) if refs else None
        savings_vals = [s.savings_sek for s in sessions if s.savings_sek is not None]
        savings = sum(savings_vals) if savings_vals else None

        solar_direct = sum(s.solar_direct_kwh or 0 for s in sessions)
        solar_battery = sum(s.solar_battery_kwh or 0 for s in sessions)
        grid_battery = sum(s.grid_battery_kwh or 0 for s in sessions)
        grid_direct = sum(s.grid_direct_kwh or 0 for s in sessions)
        renewable = solar_direct + solar_battery
        grid_total = grid_battery + grid_direct

        renewable_pct = (renewable / total_energy * 100) if total_energy > 0 else 0.0
        grid_pct = (grid_total / total_energy * 100) if total_energy > 0 else 0.0
        avg_cost = (actual_cost / total_energy) if total_energy > 0 else None

        return EVStatsResult(
            period=period,
            period_from=period_from,
            period_to=period_to,
            total_energy_kwh=round(total_energy, 2),
            actual_cost_sek=round(actual_cost, 2),
            reference_cost_sek=round(reference, 2) if reference is not None else None,
            savings_sek=round(savings, 2) if savings is not None else None,
            average_cost_sek_per_kwh=round(avg_cost, 4) if avg_cost is not None else None,
            solar_direct_kwh=round(solar_direct, 2),
            solar_battery_kwh=round(solar_battery, 2),
            grid_battery_kwh=round(grid_battery, 2),
            grid_direct_kwh=round(grid_direct, 2),
            renewable_share_percent=round(renewable_pct, 1),
            grid_share_percent=round(grid_pct, 1),
            smart_charging_savings_sek=round(savings, 2) if savings is not None else None,
            solar_contribution_sek=round(sum(s.solar_contribution_sek or 0 for s in sessions), 2),
            session_count=len(sessions),
        )
