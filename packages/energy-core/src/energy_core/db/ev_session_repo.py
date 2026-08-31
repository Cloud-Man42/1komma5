"""EV charging sessions for energy accounting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import EvChargingSessionModel


@dataclass(frozen=True, slots=True)
class EvChargingSessionRecord:
    id: int
    charger_id: int
    site_id: int
    started_at: datetime
    ended_at: datetime | None
    status: str
    meter_start_kwh: float | None
    meter_stop_kwh: float | None
    total_energy_kwh: float | None
    solar_direct_kwh: float | None
    solar_battery_kwh: float | None
    grid_battery_kwh: float | None
    grid_direct_kwh: float | None
    actual_cost_sek: float | None
    reference_cost_sek: float | None
    savings_sek: float | None
    smart_charging_savings_sek: float | None
    solar_contribution_sek: float | None
    renewable_share_pct: float | None
    grid_share_pct: float | None
    energy_quality: str | None
    cost_quality: str | None
    attribution_quality: str | None
    savings_baseline: str
    calculation_version: str
    reconciliation_delta_kwh: float | None
    reconciliation_note: str | None
    chargeamps_session_id: str | None


class EvChargingSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        charger_id: int,
        site_id: int,
        started_at: datetime,
        meter_start_kwh: float | None,
        savings_baseline: str,
        calculation_version: str,
    ) -> EvChargingSessionRecord:
        row = EvChargingSessionModel(
            charger_id=charger_id,
            site_id=site_id,
            started_at=started_at,
            status="ACTIVE",
            meter_start_kwh=meter_start_kwh,
            savings_baseline=savings_baseline,
            calculation_version=calculation_version,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def get_active_for_charger(self, charger_id: int) -> EvChargingSessionRecord | None:
        row = await self._session.scalar(
            select(EvChargingSessionModel)
            .where(
                EvChargingSessionModel.charger_id == charger_id,
                EvChargingSessionModel.status == "ACTIVE",
            )
            .order_by(EvChargingSessionModel.started_at.desc())
        )
        return self._to_record(row) if row else None

    async def list_active(self) -> list[EvChargingSessionRecord]:
        rows = await self._session.scalars(
            select(EvChargingSessionModel).where(EvChargingSessionModel.status == "ACTIVE")
        )
        return [self._to_record(r) for r in rows]

    async def get_by_id(self, session_id: int) -> EvChargingSessionRecord | None:
        row = await self._session.get(EvChargingSessionModel, session_id)
        return self._to_record(row) if row else None

    async def list_for_charger(
        self,
        charger_id: int,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        statuses: tuple[str, ...] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EvChargingSessionRecord]:
        stmt = select(EvChargingSessionModel).where(EvChargingSessionModel.charger_id == charger_id)
        if from_time is not None:
            stmt = stmt.where(EvChargingSessionModel.started_at >= from_time)
        if to_time is not None:
            stmt = stmt.where(EvChargingSessionModel.started_at <= to_time)
        if statuses:
            stmt = stmt.where(EvChargingSessionModel.status.in_(statuses))
        stmt = stmt.order_by(EvChargingSessionModel.started_at.desc()).limit(limit).offset(offset)
        rows = await self._session.scalars(stmt)
        return [self._to_record(r) for r in rows]

    async def update_totals(self, session_id: int, **fields) -> None:
        """Write derived totals onto a session without ending it.

        Lets an ACTIVE session carry its running energy and source split, so
        today's figures do not read zero while the car is still charging.
        """
        row = await self._session.get(EvChargingSessionModel, session_id)
        if row is None:
            return
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()

    async def complete(self, session_id: int, **fields) -> None:
        row = await self._session.get(EvChargingSessionModel, session_id)
        if row is None:
            return
        row.status = "COMPLETED"
        await self.update_totals(session_id, **fields)

    @staticmethod
    def _to_record(row: EvChargingSessionModel) -> EvChargingSessionRecord:
        return EvChargingSessionRecord(
            id=row.id,
            charger_id=row.charger_id,
            site_id=row.site_id,
            started_at=row.started_at,
            ended_at=row.ended_at,
            status=row.status,
            meter_start_kwh=row.meter_start_kwh,
            meter_stop_kwh=row.meter_stop_kwh,
            total_energy_kwh=row.total_energy_kwh,
            solar_direct_kwh=row.solar_direct_kwh,
            solar_battery_kwh=row.solar_battery_kwh,
            grid_battery_kwh=row.grid_battery_kwh,
            grid_direct_kwh=row.grid_direct_kwh,
            actual_cost_sek=row.actual_cost_sek,
            reference_cost_sek=row.reference_cost_sek,
            savings_sek=row.savings_sek,
            smart_charging_savings_sek=row.smart_charging_savings_sek,
            solar_contribution_sek=row.solar_contribution_sek,
            renewable_share_pct=row.renewable_share_pct,
            grid_share_pct=row.grid_share_pct,
            energy_quality=row.energy_quality,
            cost_quality=row.cost_quality,
            attribution_quality=row.attribution_quality,
            savings_baseline=row.savings_baseline,
            calculation_version=row.calculation_version,
            reconciliation_delta_kwh=row.reconciliation_delta_kwh,
            reconciliation_note=row.reconciliation_note,
            chargeamps_session_id=row.chargeamps_session_id,
        )
