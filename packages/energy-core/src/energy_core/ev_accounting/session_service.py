"""EV charging session lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter, MeterSnapshot, session_energy_from_meter
from energy_core.db.ev_session_repo import EvChargingSessionRecord, EvChargingSessionRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.ev_accounting.constants import CALCULATION_VERSION, DEFAULT_SAVINGS_BASELINE
from energy_core.ev_accounting.models import ChargerSessionState
from energy_core.ev_accounting.session_totals import session_totals_from_intervals

logger = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    """Timestamps come back naive from SQLite; sampling compares against UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class EVSessionService:
    """Detect session start/stop and manage ACTIVE sessions."""

    def __init__(self) -> None:
        self._runtime: dict[int, ChargerSessionState] = {}

    def get_runtime_state(self, charger_id: int) -> ChargerSessionState:
        return self._runtime.setdefault(charger_id, ChargerSessionState())

    async def resume_active_sessions(self, session: AsyncSession) -> int:
        """Pick an ACTIVE session back up where sampling actually left off.

        Resuming from the session's opening meter reading and start time made the
        first sample after every restart re-count the whole session: one 29 kWh
        session grew to 131 kWh over six deploys. Anchor on the last interval
        instead, and let the meter re-anchor itself — its position at that point
        was never stored, so the gap is estimated from power rather than guessed
        from the session start.
        """
        from energy_core.db.ev_interval_repo import EvChargingIntervalRepository

        repo = EvChargingSessionRepository(session)
        interval_repo = EvChargingIntervalRepository(session)
        active = await repo.list_active()
        for record in active:
            state = self.get_runtime_state(record.charger_id)
            state.last_vehicle_connected = True
            state.last_meter_kwh = None
            intervals = await interval_repo.list_for_session(record.id)
            anchor = max(i.end_time for i in intervals) if intervals else record.started_at
            state.last_sample_at = _as_utc(anchor)
        logger.info("Resumed %d active EV charging sessions", len(active))
        return len(active)

    async def process_charger(
        self,
        db: AsyncSession,
        *,
        charger: EvChargerModel,
        site: SiteModel,
        meter: MeterSnapshot,
    ) -> int | None:
        """Returns session_id if state changed, else None."""
        repo = EvChargingSessionRepository(db)
        runtime = self.get_runtime_state(charger.id)
        was_connected = runtime.last_vehicle_connected
        is_connected = meter.vehicle_connected

        active = await repo.get_active_for_charger(charger.id)

        # Session start
        if is_connected and not was_connected and active is None:
            record = await repo.create(
                charger_id=charger.id,
                site_id=site.id,
                started_at=meter.recorded_at,
                meter_start_kwh=meter.cumulative_kwh,
                savings_baseline=DEFAULT_SAVINGS_BASELINE,
                calculation_version=CALCULATION_VERSION,
            )
            runtime.last_meter_kwh = meter.cumulative_kwh
            runtime.last_sample_at = meter.recorded_at
            runtime.last_vehicle_connected = is_connected
            logger.info("EV SESSION STARTED charger_id=%s session_id=%s", charger.id, record.id)
            return record.id

        # Session stop
        if not is_connected and was_connected and active is not None:
            await self._complete_session(db, repo, active, meter, runtime)
            runtime.last_vehicle_connected = is_connected
            return active.id

        runtime.last_vehicle_connected = is_connected
        return None

    async def _complete_session(
        self,
        db: AsyncSession,
        repo: EvChargingSessionRepository,
        active: EvChargingSessionRecord,
        meter: MeterSnapshot,
        runtime: ChargerSessionState,
    ) -> None:
        from energy_core.db.ev_interval_repo import EvChargingIntervalRepository

        interval_repo = EvChargingIntervalRepository(db)
        intervals = await interval_repo.list_for_session(active.id)

        measured_kwh, quality = session_energy_from_meter(active.meter_start_kwh, meter.cumulative_kwh)
        totals = session_totals_from_intervals(
            intervals,
            measured_kwh=measured_kwh,
            meter_quality=quality,
        )

        await repo.complete(
            active.id,
            ended_at=meter.recorded_at,
            meter_stop_kwh=meter.cumulative_kwh,
            **totals.as_fields(),
        )

        logger.info(
            "EV SESSION COMPLETED session_id=%s energy=%.2f solar_direct=%.2f solar_battery=%.2f "
            "grid_battery=%.2f grid_direct=%.2f actual_cost=%.2f reference_cost=%s savings=%s quality=%s note=%s",
            active.id,
            totals.total_energy_kwh,
            totals.solar_direct_kwh,
            totals.solar_battery_kwh,
            totals.grid_battery_kwh,
            totals.grid_direct_kwh,
            totals.actual_cost_sek,
            totals.reference_cost_sek,
            totals.savings_sek,
            totals.energy_quality,
            totals.reconciliation_note,
        )
        runtime.last_meter_kwh = meter.cumulative_kwh
        runtime.last_sample_at = meter.recorded_at
