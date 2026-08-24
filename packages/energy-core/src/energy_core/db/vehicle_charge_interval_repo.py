"""Vehicle charging interval records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleChargingIntervalModel


@dataclass(frozen=True, slots=True)
class VehicleChargingIntervalRecord:
    id: int
    session_id: int
    vehicle_id: int
    charger_id: int
    start_time: datetime
    end_time: datetime
    charged_energy_kwh: float
    average_charging_power_w: float | None
    pv_production_kwh: float | None
    house_consumption_kwh: float | None
    grid_import_kwh: float | None
    grid_export_kwh: float | None
    battery_charge_kwh: float | None
    battery_discharge_kwh: float | None
    electricity_price_sek_kwh: float | None
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float
    actual_cost_sek: float
    reference_cost_sek: float | None
    savings_sek: float | None
    confidence: float | None
    data_quality: str | None


class VehicleChargingIntervalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, **fields) -> VehicleChargingIntervalRecord:
        row = VehicleChargingIntervalModel(**fields)
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def list_for_session(self, session_id: int) -> list[VehicleChargingIntervalRecord]:
        rows = await self._session.scalars(
            select(VehicleChargingIntervalModel)
            .where(VehicleChargingIntervalModel.session_id == session_id)
            .order_by(VehicleChargingIntervalModel.start_time)
        )
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: VehicleChargingIntervalModel) -> VehicleChargingIntervalRecord:
        return VehicleChargingIntervalRecord(
            id=row.id,
            session_id=row.session_id,
            vehicle_id=row.vehicle_id,
            charger_id=row.charger_id,
            start_time=row.start_time,
            end_time=row.end_time,
            charged_energy_kwh=row.charged_energy_kwh,
            average_charging_power_w=row.average_charging_power_w,
            pv_production_kwh=row.pv_production_kwh,
            house_consumption_kwh=row.house_consumption_kwh,
            grid_import_kwh=row.grid_import_kwh,
            grid_export_kwh=row.grid_export_kwh,
            battery_charge_kwh=row.battery_charge_kwh,
            battery_discharge_kwh=row.battery_discharge_kwh,
            electricity_price_sek_kwh=row.electricity_price_sek_kwh,
            solar_direct_kwh=row.solar_direct_kwh,
            solar_battery_kwh=row.solar_battery_kwh,
            grid_battery_kwh=row.grid_battery_kwh,
            grid_direct_kwh=row.grid_direct_kwh,
            actual_cost_sek=row.actual_cost_sek,
            reference_cost_sek=row.reference_cost_sek,
            savings_sek=row.savings_sek,
            confidence=row.confidence,
            data_quality=row.data_quality,
        )
