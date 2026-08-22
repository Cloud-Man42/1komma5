"""Battery energy ledger snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import BatteryEnergyLedgerModel


@dataclass(frozen=True, slots=True)
class BatteryLedgerRecord:
    site_id: int
    recorded_at: datetime
    solar_energy_kwh: float
    grid_energy_kwh: float
    grid_energy_cost_sek: float


class BatteryEnergyLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_snapshot(
        self,
        *,
        site_id: int,
        recorded_at: datetime,
        solar_energy_kwh: float,
        grid_energy_kwh: float,
        grid_energy_cost_sek: float,
    ) -> None:
        row = BatteryEnergyLedgerModel(
            site_id=site_id,
            recorded_at=recorded_at,
            solar_energy_kwh=solar_energy_kwh,
            grid_energy_kwh=grid_energy_kwh,
            grid_energy_cost_sek=grid_energy_cost_sek,
        )
        self._session.add(row)
        await self._session.flush()

    async def get_latest(self, site_id: int) -> BatteryLedgerRecord | None:
        row = await self._session.scalar(
            select(BatteryEnergyLedgerModel)
            .where(BatteryEnergyLedgerModel.site_id == site_id)
            .order_by(BatteryEnergyLedgerModel.recorded_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return BatteryLedgerRecord(
            site_id=row.site_id,
            recorded_at=row.recorded_at,
            solar_energy_kwh=row.solar_energy_kwh,
            grid_energy_kwh=row.grid_energy_kwh,
            grid_energy_cost_sek=row.grid_energy_cost_sek,
        )
