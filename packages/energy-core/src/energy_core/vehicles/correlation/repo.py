"""Halo correlation persistence for vehicles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EvChargerModel, VehicleHaloCorrelationModel, VehicleModel
from energy_core.vehicles.abstractions.models import VehicleState
from energy_core.vehicles.correlation.halo import VehicleHaloCorrelationResult, correlate_vehicle_with_halo, halo_snapshot_from_charger


@dataclass(frozen=True, slots=True)
class VehicleHaloCorrelationRecord:
    vehicle_id: int
    charger_id: int | None
    confidence: float
    status: str
    plugged_agreement: bool | None
    charging_agreement: bool | None
    power_delta_kw: float | None
    vehicle_power_kw: float | None
    halo_power_kw: float | None
    notes: str
    updated_at: datetime | None


class VehicleHaloCorrelationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, vehicle_id: int) -> VehicleHaloCorrelationRecord | None:
        row = await self._session.get(VehicleHaloCorrelationModel, vehicle_id)
        if row is None:
            return None
        return self._to_record(row)

    async def resolve_charger(self, vehicle: VehicleModel) -> EvChargerModel | None:
        if vehicle.charger_id is not None:
            return await self._session.get(EvChargerModel, vehicle.charger_id)
        result = await self._session.execute(
            select(EvChargerModel).where(EvChargerModel.site_id == vehicle.site_id).order_by(EvChargerModel.id)
        )
        chargers = list(result.scalars().all())
        if len(chargers) == 1:
            return chargers[0]
        return None

    async def correlate_and_persist(self, vehicle: VehicleModel, state: VehicleState) -> VehicleHaloCorrelationResult:
        charger = await self.resolve_charger(vehicle)
        halo = halo_snapshot_from_charger(charger) if charger is not None else None
        result = correlate_vehicle_with_halo(state, halo)
        row = await self._session.get(VehicleHaloCorrelationModel, vehicle.id)
        now = datetime.now(UTC)
        values = {
            "charger_id": result.charger_id,
            "confidence": result.confidence,
            "status": result.status.value,
            "plugged_agreement": result.plugged_agreement,
            "charging_agreement": result.charging_agreement,
            "power_delta_kw": result.power_delta_kw,
            "vehicle_power_kw": result.vehicle_power_kw,
            "halo_power_kw": result.halo_power_kw,
            "notes": result.notes[:512],
            "updated_at": now,
        }
        if row is None:
            self._session.add(VehicleHaloCorrelationModel(vehicle_id=vehicle.id, **values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        if charger is not None and vehicle.charger_id is None and result.charger_id is not None:
            vehicle.charger_id = result.charger_id
        await self._session.flush()
        return result

    async def link_charger(self, vehicle_id: int, charger_id: int | None) -> VehicleModel | None:
        vehicle = await self._session.get(VehicleModel, vehicle_id)
        if vehicle is None:
            return None
        vehicle.charger_id = charger_id
        await self._session.flush()
        return vehicle

    def _to_record(self, row: VehicleHaloCorrelationModel) -> VehicleHaloCorrelationRecord:
        return VehicleHaloCorrelationRecord(
            vehicle_id=row.vehicle_id,
            charger_id=row.charger_id,
            confidence=row.confidence,
            status=row.status,
            plugged_agreement=row.plugged_agreement,
            charging_agreement=row.charging_agreement,
            power_delta_kw=row.power_delta_kw,
            vehicle_power_kw=row.vehicle_power_kw,
            halo_power_kw=row.halo_power_kw,
            notes=row.notes,
            updated_at=row.updated_at,
        )
