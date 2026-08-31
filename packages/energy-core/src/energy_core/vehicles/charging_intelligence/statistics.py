"""Charging session analytics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleChargeSessionModel


@dataclass(frozen=True, slots=True)
class ChargingStatistics:
    period: str
    total_energy_kwh: float
    home_energy_kwh: float
    away_energy_kwh: float
    ac_energy_kwh: float
    dc_energy_kwh: float
    free_energy_kwh: float
    paid_energy_kwh: float
    avg_price_sek_kwh: float | None
    total_cost_sek: float
    savings_vs_public_sek: float | None
    solar_share_pct: float | None
    grid_share_pct: float | None
    session_count: int


def _period_start(period: str, *, now: datetime) -> datetime:
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start = now - timedelta(days=now.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unknown period: {period}")


async def compute_charging_statistics(
    session: AsyncSession,
    *,
    site_id: int,
    vehicle_id: int | None,
    period: str,
) -> ChargingStatistics:
    now = datetime.now(UTC)
    start = _period_start(period, now=now)
    query = select(VehicleChargeSessionModel).where(
        VehicleChargeSessionModel.site_id == site_id,
        VehicleChargeSessionModel.status == "COMPLETED",
        VehicleChargeSessionModel.connected_at >= start,
    )
    if vehicle_id is not None:
        query = query.where(VehicleChargeSessionModel.vehicle_id == vehicle_id)
    rows = list(await session.scalars(query))

    total_energy = 0.0
    home_energy = 0.0
    away_energy = 0.0
    ac_energy = 0.0
    dc_energy = 0.0
    free_energy = 0.0
    paid_energy = 0.0
    total_cost = 0.0
    savings = 0.0
    savings_count = 0
    solar_kwh = 0.0
    grid_kwh = 0.0

    for row in rows:
        energy = row.halo_energy_kwh or row.estimated_energy_kwh or 0.0
        total_energy += energy
        if row.home_charging:
            home_energy += energy
        elif row.home_charging is False:
            away_energy += energy
        if row.charging_type in {"AC", "UNKNOWN", None}:
            ac_energy += energy
        elif row.charging_type in {"DC", "HPC"}:
            dc_energy += energy
        cost = row.charging_cost_sek if row.charging_cost_sek is not None else (row.actual_cost_sek or 0.0)
        total_cost += cost
        if cost <= 0 and energy > 0:
            free_energy += energy
        elif energy > 0:
            paid_energy += energy
        if row.savings_sek is not None:
            savings += row.savings_sek
            savings_count += 1
        solar_kwh += (row.solar_direct_kwh or 0.0) + (row.solar_battery_kwh or 0.0)
        grid_kwh += (row.grid_direct_kwh or 0.0) + (row.grid_battery_kwh or 0.0)

    avg_price = (total_cost / paid_energy) if paid_energy > 0 else None
    renewable = solar_kwh
    renewable_pct = (renewable / total_energy * 100.0) if total_energy > 0 else None
    grid_pct = (grid_kwh / total_energy * 100.0) if total_energy > 0 else None

    return ChargingStatistics(
        period=period,
        total_energy_kwh=total_energy,
        home_energy_kwh=home_energy,
        away_energy_kwh=away_energy,
        ac_energy_kwh=ac_energy,
        dc_energy_kwh=dc_energy,
        free_energy_kwh=free_energy,
        paid_energy_kwh=paid_energy,
        avg_price_sek_kwh=avg_price,
        total_cost_sek=total_cost,
        savings_vs_public_sek=savings if savings_count else None,
        solar_share_pct=renewable_pct,
        grid_share_pct=grid_pct,
        session_count=len(rows),
    )
