"""Vehicle charge session lifecycle."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import MeterSnapshot, session_energy_from_meter
from energy_core.db.ev_interval_repo import EvChargingIntervalRepository
from energy_core.db.ev_session_repo import EvChargingSessionRepository
from energy_core.db.models import EvChargerModel, SiteModel, VehicleModel, VehicleStateLatestModel
from energy_core.db.vehicle_charge_interval_repo import VehicleChargingIntervalRepository
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRecord, VehicleChargeSessionRepository
from energy_core.ev_accounting.models import EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService
from energy_core.ev_accounting.session_totals import session_totals_from_intervals
from energy_core.vehicles.charging_intelligence.service import ChargingSessionService
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS
from energy_core.vehicles.sessions.constants import (
    CALCULATION_VERSION,
    DEFAULT_SAVINGS_BASELINE,
    estimate_battery_delta_kwh,
)
from energy_core.vehicles.sessions.models import VehicleSessionRuntimeState

logger = logging.getLogger(__name__)


def _vehicle_data_stale(latest: VehicleStateLatestModel | None) -> bool:
    if latest is None or latest.last_vehicle_update is None:
        return True
    ts = latest.last_vehicle_update
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return (datetime.now(UTC) - ts).total_seconds() > STALE_TELEMETRY_SECONDS


def _csi_fields(context, *, latest: VehicleStateLatestModel | None) -> dict:
    lat = getattr(latest, "latitude", None) if latest else None
    lon = getattr(latest, "longitude", None) if latest else None
    return {
        "latitude": lat,
        "longitude": lon,
        "location_name": context.location_name,
        "location_id": context.location_id,
        "charger_operator": context.charger_operator,
        "charging_type": context.charging_type,
        "home_charging": context.home_charging,
        "energy_source": context.energy_source,
        "estimated_energy_kwh": context.estimated_energy_kwh,
        "charging_cost_sek": context.charging_cost_sek,
        "cost_source": context.cost_source,
        "detection_confidence": context.detection_confidence,
        "identification_method": context.identification_method,
        "vehicle_data_quality": context.vehicle_data_quality,
        "charging_state": context.charging_state,
    }


class VehicleChargeSessionService:
    """Detect plug/charge sessions from Mercedes state with Halo meter energy."""

    def __init__(self) -> None:
        self._runtime: dict[int, VehicleSessionRuntimeState] = {}
        self._reconciliation = SessionReconciliationService()

    def get_runtime_state(self, vehicle_id: int) -> VehicleSessionRuntimeState:
        return self._runtime.setdefault(vehicle_id, VehicleSessionRuntimeState())

    async def resume_active_sessions(
        self,
        session: AsyncSession,
        csi: ChargingSessionService | None = None,
    ) -> int:
        repo = VehicleChargeSessionRepository(session)
        active = await repo.list_active()
        for record in active:
            state = self.get_runtime_state(record.vehicle_id)
            state.last_plugged_in = True
            state.last_meter_kwh = record.meter_start_kwh
            state.last_sample_at = record.connected_at
            state.last_soc = record.start_soc
            if csi is not None and record.charging_state:
                sm = csi.state_machine(record.vehicle_id)
                sm.restore(record.charging_state)
        logger.info("Resumed %d active vehicle charge sessions", len(active))
        return len(active)

    async def process_vehicle_without_charger(
        self,
        db: AsyncSession,
        *,
        vehicle: VehicleModel,
        site: SiteModel,
        latest: VehicleStateLatestModel | None,
        csi: ChargingSessionService,
        identification_confidence: float | None,
    ) -> int | None:
        now = datetime.now(UTC)
        repo = VehicleChargeSessionRepository(db)
        runtime = self.get_runtime_state(vehicle.id)
        is_plugged = bool(latest and latest.is_plugged_in)
        is_charging = bool(latest and latest.is_charging)
        was_plugged = runtime.last_plugged_in
        soc = latest.state_of_charge_percent if latest else None
        active = await repo.get_active_for_vehicle(vehicle.id)
        context = csi.build_context(
            vehicle=vehicle,
            site=site,
            latest=latest,
            charger=None,
            meter=None,
            previous_soc=runtime.last_soc,
        )
        csi_fields = _csi_fields(context, latest=latest)

        if is_plugged and not was_plugged and active is None:
            record = await repo.create(
                vehicle_id=vehicle.id,
                charger_id=None,
                site_id=site.id,
                connected_at=now,
                start_soc=soc,
                target_soc=latest.target_soc_percent if latest else None,
                meter_start_kwh=None,
                identification_confidence=identification_confidence,
                savings_baseline=DEFAULT_SAVINGS_BASELINE,
                calculation_version=CALCULATION_VERSION,
                **csi_fields,
            )
            runtime.last_plugged_in = is_plugged
            runtime.last_charging = is_charging
            runtime.last_soc = soc
            return record.id

        if active is not None:
            await repo.update_csi_fields(active.id, **csi_fields)
            if not is_plugged and was_plugged and not _vehicle_data_stale(latest):
                await self._complete_away_session(db, repo, active, runtime, end_soc=soc, context=context)
            elif _vehicle_data_stale(latest) and (is_charging or was_plugged):
                await repo.update_csi_fields(active.id, vehicle_data_quality="STALE")

        runtime.last_plugged_in = is_plugged
        runtime.last_charging = is_charging
        if soc is not None:
            runtime.last_soc = soc
        return None

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
        csi: ChargingSessionService,
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
        stale = _vehicle_data_stale(latest)
        charger_active = bool(meter.is_charging or meter.vehicle_connected or (meter.power_w or 0) > 0)

        context = csi.build_context(
            vehicle=vehicle,
            site=site,
            latest=latest,
            charger=charger,
            meter=meter,
            previous_soc=runtime.last_soc,
        )
        csi_fields = _csi_fields(context, latest=latest)

        active = await repo.get_active_for_vehicle(vehicle.id)

        if is_plugged and not was_plugged and active is None:
            ev_session = await EvChargingSessionRepository(db).get_active_for_charger(charger.id)
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
                ev_charging_session_id=ev_session.id if ev_session else None,
                **csi_fields,
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
            if stale and charger_active:
                await repo.update_csi_fields(active.id, vehicle_data_quality="STALE", **csi_fields)
            else:
                await self._complete_session(db, repo, active, meter, runtime, end_soc=soc, csi_fields=csi_fields)
            runtime.last_plugged_in = is_plugged
            runtime.last_charging = is_charging
            return active.id

        if active is not None:
            await repo.update_csi_fields(active.id, **csi_fields)
            if stale and (is_charging or was_charging or charger_active):
                await repo.update_csi_fields(active.id, vehicle_data_quality="STALE")
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
            if active.ev_charging_session_id is None:
                ev_session = await EvChargingSessionRepository(db).get_active_for_charger(charger.id)
                if ev_session is not None:
                    await repo.update_csi_fields(active.id, ev_charging_session_id=ev_session.id)

        runtime.last_plugged_in = is_plugged
        runtime.last_charging = is_charging
        if soc is not None:
            runtime.last_soc = soc
        return None

    async def _complete_away_session(
        self,
        db: AsyncSession,
        repo: VehicleChargeSessionRepository,
        active: VehicleChargeSessionRecord,
        runtime: VehicleSessionRuntimeState,
        *,
        end_soc: float | None,
        context,
    ) -> None:
        estimated_delta = estimate_battery_delta_kwh(active.start_soc, end_soc)
        energy = context.estimated_energy_kwh or estimated_delta
        await repo.complete(
            active.id,
            disconnected_at=datetime.now(UTC),
            end_soc=end_soc,
            halo_energy_kwh=energy,
            estimated_battery_energy_delta_kwh=estimated_delta,
            charging_cost_sek=context.charging_cost_sek,
            cost_source=context.cost_source,
            energy_quality="ESTIMATED",
            cost_quality="ESTIMATED" if context.charging_cost_sek else "INCOMPLETE",
            attribution_quality="UNAVAILABLE",
            **_csi_fields(context, latest=None),
        )
        runtime.last_plugged_in = False
        runtime.last_charging = False

    async def _complete_session(
        self,
        db: AsyncSession,
        repo: VehicleChargeSessionRepository,
        active: VehicleChargeSessionRecord,
        meter: MeterSnapshot,
        runtime: VehicleSessionRuntimeState,
        *,
        end_soc: float | None,
        csi_fields: dict | None = None,
    ) -> None:
        if active.ev_charging_session_id is not None:
            intervals = await EvChargingIntervalRepository(db).list_for_session(active.ev_charging_session_id)
        else:
            intervals = await VehicleChargingIntervalRepository(db).list_for_session(active.id)

        measured_kwh, quality = session_energy_from_meter(active.meter_start_kwh, meter.cumulative_kwh)
        if active.ev_charging_session_id is not None and intervals:
            totals = session_totals_from_intervals(
                intervals,
                measured_kwh=measured_kwh,
                meter_quality=quality,
            )
            fields = totals.as_fields()
            total = fields.pop("total_energy_kwh")
            await repo.complete(
                active.id,
                disconnected_at=meter.recorded_at,
                end_soc=end_soc,
                meter_stop_kwh=meter.cumulative_kwh,
                halo_energy_kwh=total,
                estimated_battery_energy_delta_kwh=estimate_battery_delta_kwh(active.start_soc, end_soc),
                **fields,
                **(csi_fields or {}),
            )
        else:
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
                **(csi_fields or {}),
            )

        logger.info(
            "VEHICLE SESSION COMPLETED session_id=%s vehicle_id=%s",
            active.id,
            active.vehicle_id,
        )
        runtime.last_meter_kwh = meter.cumulative_kwh
        runtime.last_sample_at = meter.recorded_at
