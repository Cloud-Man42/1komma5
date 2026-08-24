"""Vehicle charge session lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import MeterSnapshot, session_energy_from_meter
from energy_core.db.models import EvChargerModel, SiteModel, VehicleModel, VehicleStateLatestModel
from energy_core.db.vehicle_charge_interval_repo import VehicleChargingIntervalRepository
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRecord, VehicleChargeSessionRepository
from energy_core.ev_accounting.cost import EVChargingCostCalculator
from energy_core.ev_accounting.models import EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService
from energy_core.vehicles.sessions.constants import (
    CALCULATION_VERSION,
    DEFAULT_SAVINGS_BASELINE,
    SOC_TO_KWH_FACTOR,
)
from energy_core.vehicles.sessions.models import VehicleSessionRuntimeState

logger = logging.getLogger(__name__)


def estimate_battery_delta_kwh(start_soc: float | None, end_soc: float | None) -> float | None:
    if start_soc is None or end_soc is None:
        return None
    delta = end_soc - start_soc
    if delta <= 0:
        return None
    return delta * SOC_TO_KWH_FACTOR


class VehicleChargeSessionService:
    """Detect plug/charge sessions from Mercedes state with Halo meter energy."""

    def __init__(self) -> None:
        self._runtime: dict[int, VehicleSessionRuntimeState] = {}
        self._reconciliation = SessionReconciliationService()

    def get_runtime_state(self, vehicle_id: int) -> VehicleSessionRuntimeState:
        return self._runtime.setdefault(vehicle_id, VehicleSessionRuntimeState())

    async def resume_active_sessions(self, session: AsyncSession) -> int:
        repo = VehicleChargeSessionRepository(session)
        active = await repo.list_active()
        for record in active:
            state = self.get_runtime_state(record.vehicle_id)
            state.last_plugged_in = True
            state.last_meter_kwh = record.meter_start_kwh
            state.last_sample_at = record.connected_at
            state.last_soc = record.start_soc
        logger.info("Resumed %d active vehicle charge sessions", len(active))
        return len(active)

    async def process_vehicle(
        self,
        db: AsyncSession,
        *,
        vehicle: VehicleModel,
        charger: EvChargerModel,
        site: SiteModel,
        latest: VehicleStateLatestModel | None,
        meter: MeterSnapshot,
        identification_confidence: float | None,
    ) -> int | None:
        repo = VehicleChargeSessionRepository(db)
        runtime = self.get_runtime_state(vehicle.id)
        is_plugged = bool(latest and latest.is_plugged_in)
        is_charging = bool(latest and latest.is_charging)
        was_plugged = runtime.last_plugged_in
        was_charging = runtime.last_charging
        now = meter.recorded_at
        soc = latest.state_of_charge_percent if latest else None
        target_soc = latest.target_soc_percent if latest else None

        active = await repo.get_active_for_vehicle(vehicle.id)

        if is_plugged and not was_plugged and active is None:
            record = await repo.create(
                vehicle_id=vehicle.id,
                charger_id=charger.id,
                site_id=site.id,
                connected_at=now,
                start_soc=soc,
                target_soc=target_soc,
                meter_start_kwh=meter.cumulative_kwh,
                identification_confidence=identification_confidence,
                savings_baseline=DEFAULT_SAVINGS_BASELINE,
                calculation_version=CALCULATION_VERSION,
            )
            runtime.last_meter_kwh = meter.cumulative_kwh
            runtime.last_sample_at = now
            runtime.last_soc = soc
            runtime.last_plugged_in = is_plugged
            runtime.last_charging = is_charging
            if is_charging:
                await repo.update_charging_timestamps(
                    record.id,
                    charging_started_at=now,
                    target_soc=target_soc,
                )
            logger.info(
                "VEHICLE SESSION STARTED vehicle_id=%s session_id=%s confidence=%s",
                vehicle.id,
                record.id,
                identification_confidence,
            )
            return record.id

        if not is_plugged and was_plugged and active is not None:
            await self._complete_session(db, repo, active, meter, runtime, end_soc=soc)
            runtime.last_plugged_in = is_plugged
            runtime.last_charging = is_charging
            return active.id

        if active is not None:
            if is_charging and not was_charging:
                await repo.update_charging_timestamps(
                    active.id,
                    charging_started_at=now,
                    target_soc=target_soc,
                )
            elif not is_charging and was_charging:
                await repo.update_charging_timestamps(active.id, charging_stopped_at=now)
            elif target_soc is not None:
                await repo.update_charging_timestamps(active.id, target_soc=target_soc)

        runtime.last_plugged_in = is_plugged
        runtime.last_charging = is_charging
        if soc is not None:
            runtime.last_soc = soc
        return None

    async def _complete_session(
        self,
        db: AsyncSession,
        repo: VehicleChargeSessionRepository,
        active: VehicleChargeSessionRecord,
        meter: MeterSnapshot,
        runtime: VehicleSessionRuntimeState,
        *,
        end_soc: float | None,
    ) -> None:
        interval_repo = VehicleChargingIntervalRepository(db)
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

        actual_cost = sum(i.actual_cost_sek for i in intervals)
        reference_cost = sum(i.reference_cost_sek for i in intervals if i.reference_cost_sek is not None)
        reference_cost = reference_cost if reference_cost > 0 else None
        savings = (reference_cost - actual_cost) if reference_cost is not None else None

        total = recon.attribution.total_kwh or measured_kwh or 0.0
        renewable = recon.attribution.renewable_kwh
        renewable_pct = (renewable / total * 100.0) if total > 0 else 0.0
        grid_pct = (recon.attribution.grid_kwh / total * 100.0) if total > 0 else 0.0
        estimated_delta = estimate_battery_delta_kwh(active.start_soc, end_soc)

        if active.charging_started_at and active.charging_stopped_at is None:
            await repo.update_charging_timestamps(active.id, charging_stopped_at=meter.recorded_at)

        await repo.complete(
            active.id,
            disconnected_at=meter.recorded_at,
            end_soc=end_soc,
            meter_stop_kwh=meter.cumulative_kwh,
            halo_energy_kwh=total,
            estimated_battery_energy_delta_kwh=estimated_delta,
            solar_direct_kwh=recon.attribution.solar_direct_kwh,
            solar_battery_kwh=recon.attribution.solar_battery_kwh,
            grid_battery_kwh=recon.attribution.grid_battery_kwh,
            grid_direct_kwh=recon.attribution.grid_direct_kwh,
            actual_cost_sek=actual_cost,
            reference_cost_sek=reference_cost,
            savings_sek=savings,
            renewable_share_pct=renewable_pct,
            grid_share_pct=grid_pct,
            energy_quality=recon.energy_quality if quality == "MEASURED" else quality,
            cost_quality="CALCULATED" if reference_cost else "INCOMPLETE",
            attribution_quality="CALCULATED",
            reconciliation_delta_kwh=recon.delta_kwh,
            reconciliation_note=recon.note,
        )

        logger.info(
            "VEHICLE SESSION COMPLETED session_id=%s vehicle_id=%s energy=%.2f quality=%s",
            active.id,
            active.vehicle_id,
            total,
            recon.energy_quality,
        )
        runtime.last_meter_kwh = meter.cumulative_kwh
        runtime.last_sample_at = meter.recorded_at
