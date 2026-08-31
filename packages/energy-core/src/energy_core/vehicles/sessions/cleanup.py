"""Remove vehicle charge history that records nothing.

Two artefacts accumulated while `persist_state` let an empty discovery overwrite
good telemetry: charge sessions opened and closed on a plug-in that never
charged, and state history rows with no telemetry at all. Neither carries
information, but both show up as sessions and readings in the dashboard.

The real charging history lives in `ev_charging_sessions` (the charger's own
meter) and is never touched here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import (
    VehicleChargeSessionModel,
    VehicleChargingIntervalModel,
    VehicleStateHistoryModel,
)

_TELEMETRY_COLUMNS = (
    VehicleStateHistoryModel.state_of_charge_percent,
    VehicleStateHistoryModel.target_soc_percent,
    VehicleStateHistoryModel.electric_range_km,
    VehicleStateHistoryModel.is_plugged_in,
    VehicleStateHistoryModel.is_charging,
    VehicleStateHistoryModel.charging_power_kw,
)


@dataclass(frozen=True, slots=True)
class EmptySession:
    session_id: int
    vehicle_id: int
    status: str
    connected_at: datetime
    disconnected_at: datetime | None


@dataclass(frozen=True, slots=True)
class CleanupResult:
    sessions: tuple[EmptySession, ...]
    state_rows: int

    @property
    def total(self) -> int:
        return len(self.sessions) + self.state_rows


async def find_empty_sessions(
    db: AsyncSession,
    *,
    site_id: int | None = None,
) -> tuple[EmptySession, ...]:
    """Closed sessions that never charged: no start, no intervals, no energy.

    An ACTIVE session is left alone even when empty — the car may be plugged in
    right now and about to charge into it.
    """
    interval_count = (
        select(func.count(VehicleChargingIntervalModel.id))
        .where(VehicleChargingIntervalModel.session_id == VehicleChargeSessionModel.id)
        .scalar_subquery()
    )
    stmt = select(VehicleChargeSessionModel).where(
        VehicleChargeSessionModel.status != "ACTIVE",
        VehicleChargeSessionModel.charging_started_at.is_(None),
        VehicleChargeSessionModel.charging_stopped_at.is_(None),
        interval_count == 0,
        func.coalesce(VehicleChargeSessionModel.halo_energy_kwh, 0.0) == 0.0,
        func.coalesce(VehicleChargeSessionModel.estimated_battery_energy_delta_kwh, 0.0) == 0.0,
        func.coalesce(VehicleChargeSessionModel.solar_direct_kwh, 0.0) == 0.0,
        func.coalesce(VehicleChargeSessionModel.solar_battery_kwh, 0.0) == 0.0,
        func.coalesce(VehicleChargeSessionModel.grid_battery_kwh, 0.0) == 0.0,
        func.coalesce(VehicleChargeSessionModel.grid_direct_kwh, 0.0) == 0.0,
    )
    if site_id is not None:
        stmt = stmt.where(VehicleChargeSessionModel.site_id == site_id)
    rows = await db.scalars(stmt.order_by(VehicleChargeSessionModel.id))
    return tuple(
        EmptySession(
            session_id=row.id,
            vehicle_id=row.vehicle_id,
            status=row.status,
            connected_at=row.connected_at,
            disconnected_at=row.disconnected_at,
        )
        for row in rows
    )


async def count_empty_state_rows(db: AsyncSession) -> int:
    """State history rows a discovery wrote: every telemetry column is NULL."""
    stmt = select(func.count()).select_from(VehicleStateHistoryModel)
    for column in _TELEMETRY_COLUMNS:
        stmt = stmt.where(column.is_(None))
    return int(await db.scalar(stmt) or 0)


async def purge_empty_history(
    db: AsyncSession,
    *,
    site_id: int | None = None,
    include_state_rows: bool = True,
    dry_run: bool = True,
) -> CleanupResult:
    sessions = await find_empty_sessions(db, site_id=site_id)
    state_rows = await count_empty_state_rows(db) if include_state_rows else 0

    if not dry_run:
        if sessions:
            ids = [s.session_id for s in sessions]
            await db.execute(
                delete(VehicleChargingIntervalModel).where(
                    VehicleChargingIntervalModel.session_id.in_(ids)
                )
            )
            await db.execute(
                delete(VehicleChargeSessionModel).where(VehicleChargeSessionModel.id.in_(ids))
            )
        if include_state_rows and state_rows:
            stmt = delete(VehicleStateHistoryModel)
            for column in _TELEMETRY_COLUMNS:
                stmt = stmt.where(column.is_(None))
            await db.execute(stmt)

    return CleanupResult(sessions=sessions, state_rows=state_rows)
