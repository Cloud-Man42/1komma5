"""Sample spa energy intervals with attribution and cost."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.consumer_accounting.attribution import ConsumerAttributionEngine
from energy_core.consumer_accounting.cost import ConsumerCostCalculator
from energy_core.consumer_accounting.types import DataQuality, SpaEnergySample
from energy_core.db.battery_ledger_repo import BatteryEnergyLedgerRepository
from energy_core.db.consumer_repo import ConsumerIntervalRepository
from energy_core.db.models import SiteModel
from energy_core.db.repositories import MarketPriceRepository
from energy_core.ev_accounting.battery_ledger import BatteryEnergyLedgerService
from energy_core.ev_accounting.models import BatteryLedgerState, SiteEnergySample
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus

logger = logging.getLogger(__name__)


class ConsumerSampler:
    def __init__(self) -> None:
        self._attribution = ConsumerAttributionEngine()
        self._cost = ConsumerCostCalculator()
        self._ledger_service = BatteryEnergyLedgerService()

    async def record_interval(
        self,
        db: AsyncSession,
        *,
        consumer_id: int,
        site: SiteModel,
        spa_sample: SpaEnergySample,
        site_sample: SiteEnergySample | None,
        start_time: datetime,
        end_time: datetime,
        is_sqlite: bool,
        cost_enabled: bool,
    ) -> None:
        energy_kwh = spa_sample.energy_delta_kwh
        if energy_kwh <= 0:
            return

        duration_hours = max(0.0, (end_time - start_time).total_seconds() / 3600.0)
        if duration_hours <= 0:
            return

        price_repo = MarketPriceRepository(db, is_sqlite=is_sqlite)
        hour = end_time.replace(minute=0, second=0, microsecond=0)
        price = site_sample.electricity_price_sek_kwh if site_sample else None
        if price is None:
            mp = await price_repo.get_at(site.id, hour)
            price = mp.all_in_price_sek_kwh if mp and mp.all_in_price_sek_kwh else site.fallback_purchase_price_sek_kwh

        ledger_repo = BatteryEnergyLedgerRepository(db)
        ledger_row = await ledger_repo.get_latest(site.id)
        ledger_state = BatteryLedgerState(
            solar_energy_kwh=ledger_row.solar_energy_kwh if ledger_row else 0.0,
            grid_energy_kwh=ledger_row.grid_energy_kwh if ledger_row else 0.0,
            grid_energy_cost_sek=ledger_row.grid_energy_cost_sek if ledger_row else 0.0,
        )

        sample = site_sample or SiteEnergySample(
            pv_power_w=0.0,
            house_consumption_w=spa_sample.power_w,
            grid_import_w=spa_sample.power_w,
            grid_export_w=0.0,
            battery_charge_w=0.0,
            battery_discharge_w=0.0,
            ev_power_w=0.0,
            electricity_price_sek_kwh=price,
            duration_hours=duration_hours,
        )

        _, discharge_split = self._ledger_service.update(
            ledger_state,
            sample,
            grid_price_sek_kwh=price or site.fallback_purchase_price_sek_kwh,
        )

        attr_result = self._attribution.attribute_interval(
            energy_kwh,
            sample,
            battery_discharge=discharge_split,
            ev_power_w=spa_sample.power_w,
        )
        unknown_kwh = max(
            0.0,
            energy_kwh - attr_result.attribution.total_kwh,
        )
        cost_result = self._cost.interval_costs(
            attr_result.attribution,
            grid_price_sek_kwh=price,
            grid_battery_avg_cost_sek_kwh=ledger_state.grid_avg_cost_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
        ) if cost_enabled else None

        avg_power = spa_sample.power_w
        heater_runtime = duration_hours * 3600.0 if spa_sample.heater_active else 0.0
        pump_runtime = duration_hours * 3600.0 if any(v != "off" for v in spa_sample.pump_states.values()) else 0.0

        interval_repo = ConsumerIntervalRepository(db)
        await interval_repo.insert(
            consumer_id=consumer_id,
            start_time=start_time,
            end_time=end_time,
            energy_kwh=energy_kwh,
            average_power_w=avg_power,
            pv_production_kwh=sample.pv_kwh,
            house_consumption_kwh=sample.house_kwh,
            grid_import_kwh=sample.grid_import_kwh,
            grid_export_kwh=sample.grid_export_kwh,
            battery_charge_kwh=sample.battery_charge_kwh,
            battery_discharge_kwh=sample.battery_discharge_kwh,
            electricity_price_sek_kwh=price,
            solar_direct_kwh=attr_result.attribution.solar_direct_kwh,
            solar_battery_kwh=attr_result.attribution.solar_battery_kwh,
            grid_battery_kwh=attr_result.attribution.grid_battery_kwh,
            grid_direct_kwh=attr_result.attribution.grid_direct_kwh,
            unknown_kwh=unknown_kwh,
            actual_cost_sek=cost_result.actual_cash_cost_sek if cost_result else 0.0,
            reference_cost_sek=cost_result.reference_cost_sek if cost_result else None,
            savings_sek=cost_result.savings_sek if cost_result else None,
            heater_runtime_seconds=heater_runtime,
            pump_runtime_seconds=pump_runtime,
            confidence=attr_result.confidence,
            data_quality=spa_sample.quality.value if isinstance(spa_sample.quality, DataQuality) else str(spa_sample.quality),
        )

    @staticmethod
    def parse_last_status(raw: str) -> ArcticSpaStatus | None:
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return ArcticSpaStatus.from_api(payload)
