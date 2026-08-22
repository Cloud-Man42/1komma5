"""EV charging session lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import ChargeAmpsMeterAdapter, MeterSnapshot, session_energy_from_meter
from energy_core.db.ev_session_repo import EvChargingSessionRecord, EvChargingSessionRepository
from energy_core.db.models import EvChargerModel, SiteModel
from energy_core.ev_accounting.constants import CALCULATION_VERSION, DEFAULT_SAVINGS_BASELINE
from energy_core.ev_accounting.models import ChargerSessionState, EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService

logger = logging.getLogger(__name__)


class EVSessionService:
    """Detect session start/stop and manage ACTIVE sessions."""

    def __init__(self) -> None:
        self._runtime: dict[int, ChargerSessionState] = {}
        self._reconciliation = SessionReconciliationService()

    def get_runtime_state(self, charger_id: int) -> ChargerSessionState:
        return self._runtime.setdefault(charger_id, ChargerSessionState())

    async def resume_active_sessions(self, session: AsyncSession) -> int:
        repo = EvChargingSessionRepository(session)
        active = await repo.list_active()
        for record in active:
            state = self.get_runtime_state(record.charger_id)
            state.last_vehicle_connected = True
            state.last_meter_kwh = record.meter_start_kwh
            state.last_sample_at = record.started_at
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
        from energy_core.ev_accounting.cost import EVChargingCostCalculator

        interval_repo = EvChargingIntervalRepository(db)
        intervals = await interval_repo.list_for_session(active.id)

        measured_kwh, quality = session_energy_from_meter(active.meter_start_kwh, meter.cumulative_kwh)
        if measured_kwh is None:
            measured_kwh = sum(i.charged_energy_kwh for i in intervals)
            quality = "ESTIMATED"

        attr = EnergyAttribution(
            solar_direct_kwh=sum(i.solar_direct_kwh for i in intervals),
            solar_battery_kwh=sum(i.solar_battery_kwh for i in intervals),
            grid_battery_kwh=sum(i.grid_battery_kwh for i in intervals),
            grid_direct_kwh=sum(i.grid_direct_kwh for i in intervals),
        )
        attributed_kwh = sum(i.charged_energy_kwh for i in intervals)

        recon = self._reconciliation.reconcile(
            attr,
            measured_kwh=measured_kwh,
            attributed_kwh=attributed_kwh,
        )

        cost_calc = EVChargingCostCalculator()
        actual_cost = sum(i.actual_cost_sek for i in intervals)
        reference_cost = sum(i.reference_cost_sek for i in intervals if i.reference_cost_sek is not None)
        reference_cost = reference_cost if reference_cost > 0 else None
        savings = (reference_cost - actual_cost) if reference_cost is not None else None
        solar_contrib = sum(
            cost_calc.solar_contribution_sek(
                EnergyAttribution(i.solar_direct_kwh, i.solar_battery_kwh, i.grid_battery_kwh, i.grid_direct_kwh),
                grid_price_sek_kwh=i.electricity_price_sek_kwh,
            )
            for i in intervals
        )

        total = recon.attribution.total_kwh or measured_kwh or 0.0
        renewable = recon.attribution.renewable_kwh
        renewable_pct = (renewable / total * 100.0) if total > 0 else 0.0
        grid_pct = (recon.attribution.grid_kwh / total * 100.0) if total > 0 else 0.0

        await repo.complete(
            active.id,
            ended_at=meter.recorded_at,
            meter_stop_kwh=meter.cumulative_kwh,
            total_energy_kwh=total,
            solar_direct_kwh=recon.attribution.solar_direct_kwh,
            solar_battery_kwh=recon.attribution.solar_battery_kwh,
            grid_battery_kwh=recon.attribution.grid_battery_kwh,
            grid_direct_kwh=recon.attribution.grid_direct_kwh,
            actual_cost_sek=actual_cost,
            reference_cost_sek=reference_cost,
            savings_sek=savings,
            smart_charging_savings_sek=savings,
            solar_contribution_sek=solar_contrib,
            renewable_share_pct=renewable_pct,
            grid_share_pct=grid_pct,
            energy_quality=recon.energy_quality if quality == "MEASURED" else quality,
            cost_quality="CALCULATED" if reference_cost else "INCOMPLETE",
            attribution_quality="CALCULATED",
            reconciliation_delta_kwh=recon.delta_kwh,
            reconciliation_note=recon.note,
        )

        logger.info(
            "EV SESSION COMPLETED session_id=%s energy=%.2f solar_direct=%.2f solar_battery=%.2f "
            "grid_battery=%.2f grid_direct=%.2f actual_cost=%.2f reference_cost=%s savings=%s quality=%s",
            active.id,
            total,
            recon.attribution.solar_direct_kwh,
            recon.attribution.solar_battery_kwh,
            recon.attribution.grid_battery_kwh,
            recon.attribution.grid_direct_kwh,
            actual_cost,
            reference_cost,
            savings,
            recon.energy_quality,
        )
        runtime.last_meter_kwh = meter.cumulative_kwh
        runtime.last_sample_at = meter.recorded_at
