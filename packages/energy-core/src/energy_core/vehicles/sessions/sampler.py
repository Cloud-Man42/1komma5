"""Sample vehicle charging intervals during active sessions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.chargers.meter_adapter import MeterSnapshot, integrate_power_kwh
from energy_core.db.battery_ledger_repo import BatteryEnergyLedgerRepository
from energy_core.db.models import EvChargerModel, SiteModel, VehicleModel
from energy_core.db.repositories import MarketPriceRepository
from energy_core.db.vehicle_charge_interval_repo import VehicleChargingIntervalRepository
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRepository
from energy_core.ev_accounting.attribution import EnergyAttributionEngine
from energy_core.ev_accounting.battery_ledger import BatteryEnergyLedgerService
from energy_core.ev_accounting.cost import EVChargingCostCalculator
from energy_core.ev_accounting.models import BatteryLedgerState, SiteEnergySample
from energy_core.vehicles.sessions.session_service import VehicleChargeSessionService

logger = logging.getLogger(__name__)


class VehicleChargeSessionSampler:
    def __init__(self, session_service: VehicleChargeSessionService) -> None:
        self._sessions = session_service
        self._ledger_service = BatteryEnergyLedgerService()
        self._attribution = EnergyAttributionEngine()
        self._cost = EVChargingCostCalculator()

    async def sample_active_session(
        self,
        db: AsyncSession,
        *,
        vehicle: VehicleModel,
        charger: EvChargerModel,
        site: SiteModel,
        meter: MeterSnapshot,
        energy_sample: SiteEnergySample,
        is_sqlite: bool,
        is_charging: bool,
    ) -> None:
        session_repo = VehicleChargeSessionRepository(db)
        active = await session_repo.get_active_for_vehicle(vehicle.id)
        if active is None:
            return
        if not is_charging and (meter.power_w or 0) <= 0:
            return

        runtime = self._sessions.get_runtime_state(vehicle.id)
        interval_repo = VehicleChargingIntervalRepository(db)
        ledger_repo = BatteryEnergyLedgerRepository(db)
        price_repo = MarketPriceRepository(db, is_sqlite=is_sqlite)

        now = meter.recorded_at
        start = runtime.last_sample_at or active.connected_at
        duration_hours = max(0.0, (now - start).total_seconds() / 3600.0)
        if duration_hours <= 0:
            return

        charged_kwh = 0.0
        quality = "ESTIMATED"
        if runtime.last_meter_kwh is not None and meter.cumulative_kwh is not None:
            delta = meter.cumulative_kwh - runtime.last_meter_kwh
            if delta >= 0:
                charged_kwh = delta
                quality = "MEASURED"
        if charged_kwh <= 0 and meter.power_w:
            charged_kwh = integrate_power_kwh(meter.power_w, duration_hours)
            quality = "ESTIMATED"
        if charged_kwh <= 0 and energy_sample.ev_power_w > 0:
            charged_kwh = integrate_power_kwh(energy_sample.ev_power_w, duration_hours)
            quality = "ESTIMATED"
        if charged_kwh <= 0:
            runtime.last_sample_at = now
            return

        ledger_row = await ledger_repo.get_latest(site.id)
        ledger_state = BatteryLedgerState(
            solar_energy_kwh=ledger_row.solar_energy_kwh if ledger_row else 0.0,
            grid_energy_kwh=ledger_row.grid_energy_kwh if ledger_row else 0.0,
            grid_energy_cost_sek=ledger_row.grid_energy_cost_sek if ledger_row else 0.0,
        )
        price = energy_sample.electricity_price_sek_kwh
        if price is None:
            hour = now.replace(minute=0, second=0, microsecond=0)
            mp = await price_repo.get_at(site.id, hour)
            price = mp.all_in_price_sek_kwh if mp and mp.all_in_price_sek_kwh else site.fallback_purchase_price_sek_kwh

        _, discharge_split = self._ledger_service.update(
            ledger_state,
            energy_sample,
            grid_price_sek_kwh=price or site.fallback_purchase_price_sek_kwh,
        )
        attr_result = self._attribution.attribute_interval(
            charged_kwh,
            energy_sample,
            battery_discharge=discharge_split,
            ev_power_w=meter.power_w or energy_sample.ev_power_w,
        )
        cost_result = self._cost.interval_costs(
            attr_result.attribution,
            grid_price_sek_kwh=price,
            grid_battery_avg_cost_sek_kwh=ledger_state.grid_avg_cost_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        )
        avg_power = charged_kwh * 1000.0 / duration_hours if duration_hours > 0 else 0.0
        await interval_repo.insert(
            session_id=active.id,
            vehicle_id=vehicle.id,
            charger_id=charger.id,
            start_time=start,
            end_time=now,
            charged_energy_kwh=charged_kwh,
            average_charging_power_w=avg_power,
            pv_production_kwh=energy_sample.pv_kwh,
            house_consumption_kwh=energy_sample.house_kwh,
            grid_import_kwh=energy_sample.grid_import_kwh,
            grid_export_kwh=energy_sample.grid_export_kwh,
            battery_charge_kwh=energy_sample.battery_charge_kwh,
            battery_discharge_kwh=energy_sample.battery_discharge_kwh,
            electricity_price_sek_kwh=price,
            solar_direct_kwh=attr_result.attribution.solar_direct_kwh,
            solar_battery_kwh=attr_result.attribution.solar_battery_kwh,
            grid_battery_kwh=attr_result.attribution.grid_battery_kwh,
            grid_direct_kwh=attr_result.attribution.grid_direct_kwh,
            actual_cost_sek=cost_result.actual_cash_cost_sek,
            reference_cost_sek=cost_result.reference_cost_sek,
            savings_sek=cost_result.savings_sek,
            confidence=attr_result.confidence,
            data_quality=quality if quality == "MEASURED" else attr_result.data_quality,
        )
        runtime.last_meter_kwh = meter.cumulative_kwh
        runtime.last_sample_at = now
