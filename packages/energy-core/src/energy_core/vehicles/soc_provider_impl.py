"""Vehicle SoC provider implementations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.soc_providers import VehicleSocSnapshot


class ManualVehicleSocProvider:
    def __init__(self, soc_pct: float) -> None:
        self._soc_pct = soc_pct

    async def get_soc(self, vehicle_id: str) -> VehicleSocSnapshot | None:
        return VehicleSocSnapshot(soc_pct=self._soc_pct, source="manual", vehicle_id=vehicle_id)


class MercedesVehicleSocProvider:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_soc(self, vehicle_id: str) -> VehicleSocSnapshot | None:
        try:
            vid = int(vehicle_id)
        except ValueError:
            return None
        result = await self._session.execute(
            select(VehicleStateLatestModel).where(VehicleStateLatestModel.vehicle_id == vid)
        )
        row = result.scalar_one_or_none()
        if row is None or row.state_of_charge_percent is None:
            return None
        return VehicleSocSnapshot(soc_pct=float(row.state_of_charge_percent), source="mercedes", vehicle_id=vehicle_id)
