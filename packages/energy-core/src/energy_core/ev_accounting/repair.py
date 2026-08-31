"""Recompute stored session totals from the intervals that back them.

Two defects left the stored figures wrong, and both are repairable because the
per-minute intervals were never damaged:

* Sessions completed before the meter-reset fix had their energy and source
  split scaled to a meter delta of zero, so a session showed 0 kWh next to a
  real cost and fell back to labelling everything grid.
* Restarting the collector used to re-anchor sampling to the session start, so
  the next sample wrote one interval re-counting everything charged so far.
  Those duplicates are removed here before the totals are rebuilt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import session_energy_from_meter
from energy_core.db.ev_interval_repo import EvChargingIntervalRecord, EvChargingIntervalRepository
from energy_core.db.ev_session_repo import EvChargingSessionRepository
from energy_core.db.models import EvChargingIntervalModel, EvChargingSessionModel
from energy_core.ev_accounting.constants import ATTRIBUTION_TOLERANCE_KWH
from energy_core.ev_accounting.session_totals import session_totals_from_intervals

logger = logging.getLogger(__name__)

REPAIRABLE_STATUSES = ("COMPLETED", "ACTIVE", "ESTIMATED", "INCOMPLETE")


@dataclass(frozen=True, slots=True)
class SessionRepair:
    session_id: int
    status: str
    interval_count: int
    removed_intervals: int
    removed_kwh: float
    old_total_kwh: float
    new_total_kwh: float
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float
    note: str


def _resume_duplicates(
    intervals: list[EvChargingIntervalRecord],
    session_started_at,
) -> list[EvChargingIntervalRecord]:
    """Intervals that re-count the session from its very beginning.

    Each restart wrote a row spanning the session start up to that moment, so
    they all share the session's start time. The shortest one is the genuine
    first interval; the rest are re-counts.
    """
    from_start = sorted(
        (i for i in intervals if i.start_time == session_started_at),
        key=lambda i: i.end_time,
    )
    return from_start[1:]


async def repair_sessions(
    db: AsyncSession,
    *,
    site_id: int | None = None,
    dry_run: bool = True,
) -> list[SessionRepair]:
    """Drop re-counted intervals and rebuild every session's stored totals.

    Idempotent: a session already matching its intervals is left untouched, so
    this is safe to re-run. An ACTIVE session keeps its status.
    """
    query = select(EvChargingSessionModel).where(EvChargingSessionModel.status.in_(REPAIRABLE_STATUSES))
    if site_id is not None:
        query = query.where(EvChargingSessionModel.site_id == site_id)
    rows = list(await db.scalars(query.order_by(EvChargingSessionModel.started_at)))

    interval_repo = EvChargingIntervalRepository(db)
    session_repo = EvChargingSessionRepository(db)
    repairs: list[SessionRepair] = []

    for row in rows:
        intervals = await interval_repo.list_for_session(row.id)
        duplicates = _resume_duplicates(intervals, row.started_at)
        if duplicates:
            duplicate_ids = {i.id for i in duplicates}
            intervals = [i for i in intervals if i.id not in duplicate_ids]
        if not intervals:
            continue

        # An ACTIVE session's meter total is not final, so the intervals decide.
        measured_kwh, quality = (
            (None, "ESTIMATED")
            if row.status == "ACTIVE"
            else session_energy_from_meter(row.meter_start_kwh, row.meter_stop_kwh)
        )
        totals = session_totals_from_intervals(intervals, measured_kwh=measured_kwh, meter_quality=quality)

        old_total = row.total_energy_kwh or 0.0
        unchanged = abs(totals.total_energy_kwh - old_total) <= ATTRIBUTION_TOLERANCE_KWH
        if not duplicates and unchanged:
            continue

        repairs.append(
            SessionRepair(
                session_id=row.id,
                status=row.status,
                interval_count=len(intervals),
                removed_intervals=len(duplicates),
                removed_kwh=sum(i.charged_energy_kwh for i in duplicates),
                old_total_kwh=old_total,
                new_total_kwh=totals.total_energy_kwh,
                solar_direct_kwh=totals.solar_direct_kwh,
                solar_battery_kwh=totals.solar_battery_kwh,
                grid_battery_kwh=totals.grid_battery_kwh,
                grid_direct_kwh=totals.grid_direct_kwh,
                note=totals.reconciliation_note,
            )
        )
        if dry_run:
            continue

        for duplicate in duplicates:
            await db.delete(await db.get(EvChargingIntervalModel, duplicate.id))
        await session_repo.update_totals(row.id, **totals.as_fields())
        logger.info(
            "EV SESSION REPAIRED session_id=%s %.2f -> %.2f kWh from %d intervals "
            "(dropped %d re-counted) note=%s",
            row.id,
            old_total,
            totals.total_energy_kwh,
            len(intervals),
            len(duplicates),
            totals.reconciliation_note,
        )

    if not dry_run and repairs:
        await db.commit()
    return repairs
