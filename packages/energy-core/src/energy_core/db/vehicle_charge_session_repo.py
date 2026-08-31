"""Vehicle charge session persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleChargeSessionModel


@dataclass(frozen=True, slots=True)
class VehicleChargeSessionRecord:
    id: int
    vehicle_id: int
    charger_id: int | None
    site_id: int
    ev_charging_session_id: int | None
    connected_at: datetime
    disconnected_at: datetime | None
    charging_started_at: datetime | None
    charging_stopped_at: datetime | None
    start_soc: float | None
    end_soc: float | None
    target_soc: float | None
    status: str
    meter_start_kwh: float | None
    meter_stop_kwh: float | None
    halo_energy_kwh: float | None
    estimated_battery_energy_delta_kwh: float | None
    solar_direct_kwh: float | None
    solar_battery_kwh: float | None
    grid_battery_kwh: float | None
    grid_direct_kwh: float | None
    actual_cost_sek: float | None
    reference_cost_sek: float | None
    savings_sek: float | None
    renewable_share_pct: float | None
    grid_share_pct: float | None
    identification_confidence: float | None
    energy_quality: str | None
    cost_quality: str | None
    attribution_quality: str | None
    savings_baseline: str
    calculation_version: str
    reconciliation_delta_kwh: float | None
    reconciliation_note: str | None
    latitude: float | None = None
    longitude: float | None = None
    location_id: int | None = None
    location_name: str | None = None
    charger_operator: str | None = None
    charger_network: str | None = None
    charging_type: str | None = None
    connector_type: str | None = None
    home_charging: bool | None = None
    energy_source: str | None = None
    estimated_energy_kwh: float | None = None
    charging_power_avg_kw: float | None = None
    charging_power_max_kw: float | None = None
    charging_cost_sek: float | None = None
    cost_source: str | None = None
    detection_confidence: str | None = None
    identification_method: str | None = None
    vehicle_data_quality: str | None = None
    charging_state: str | None = None


class VehicleChargeSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        vehicle_id: int,
        charger_id: int | None,
        site_id: int,
        connected_at: datetime,
        start_soc: float | None,
        target_soc: float | None,
        meter_start_kwh: float | None,
        identification_confidence: float | None,
        savings_baseline: str,
        calculation_version: str,
        ev_charging_session_id: int | None = None,
        **csi_fields,
    ) -> VehicleChargeSessionRecord:
        row = VehicleChargeSessionModel(
            vehicle_id=vehicle_id,
            charger_id=charger_id,
            site_id=site_id,
            connected_at=connected_at,
            start_soc=start_soc,
            target_soc=target_soc,
            meter_start_kwh=meter_start_kwh,
            identification_confidence=identification_confidence,
            savings_baseline=savings_baseline,
            calculation_version=calculation_version,
            ev_charging_session_id=ev_charging_session_id,
            status="ACTIVE",
            **{k: v for k, v in csi_fields.items() if hasattr(VehicleChargeSessionModel, k)},
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def get_active_for_vehicle(self, vehicle_id: int) -> VehicleChargeSessionRecord | None:
        row = await self._session.scalar(
            select(VehicleChargeSessionModel)
            .where(
                VehicleChargeSessionModel.vehicle_id == vehicle_id,
                VehicleChargeSessionModel.status == "ACTIVE",
            )
            .order_by(VehicleChargeSessionModel.connected_at.desc())
        )
        return self._to_record(row) if row else None

    async def list_active(self) -> list[VehicleChargeSessionRecord]:
        rows = await self._session.scalars(
            select(VehicleChargeSessionModel).where(VehicleChargeSessionModel.status == "ACTIVE")
        )
        return [self._to_record(row) for row in rows]

    async def get_by_id(self, session_id: int) -> VehicleChargeSessionRecord | None:
        row = await self._session.get(VehicleChargeSessionModel, session_id)
        return self._to_record(row) if row else None

    async def list_for_vehicle(
        self,
        vehicle_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[VehicleChargeSessionRecord]:
        rows = await self._session.scalars(
            select(VehicleChargeSessionModel)
            .where(VehicleChargeSessionModel.vehicle_id == vehicle_id)
            .order_by(VehicleChargeSessionModel.connected_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_record(row) for row in rows]

    async def get_current_for_vehicle(self, vehicle_id: int) -> VehicleChargeSessionRecord | None:
        return await self.get_active_for_vehicle(vehicle_id)

    async def update_charging_timestamps(
        self,
        session_id: int,
        *,
        charging_started_at: datetime | None = None,
        charging_stopped_at: datetime | None = None,
        target_soc: float | None = None,
    ) -> None:
        row = await self._session.get(VehicleChargeSessionModel, session_id)
        if row is None:
            return
        if charging_started_at is not None:
            row.charging_started_at = charging_started_at
        if charging_stopped_at is not None:
            row.charging_stopped_at = charging_stopped_at
        if target_soc is not None:
            row.target_soc = target_soc
        await self._session.flush()

    async def update_csi_fields(self, session_id: int, **fields) -> None:
        row = await self._session.get(VehicleChargeSessionModel, session_id)
        if row is None:
            return
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()

    async def patch_session(self, session_id: int, **fields) -> VehicleChargeSessionRecord | None:
        row = await self._session.get(VehicleChargeSessionModel, session_id)
        if row is None:
            return None
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()
        return self._to_record(row)

    async def complete(self, session_id: int, **fields) -> None:
        row = await self._session.get(VehicleChargeSessionModel, session_id)
        if row is None:
            return
        row.status = "COMPLETED"
        for key, value in fields.items():
            if hasattr(row, key):
                setattr(row, key, value)
        await self._session.flush()

    @staticmethod
    def _to_record(row: VehicleChargeSessionModel) -> VehicleChargeSessionRecord:
        return VehicleChargeSessionRecord(
            id=row.id,
            vehicle_id=row.vehicle_id,
            charger_id=row.charger_id,
            site_id=row.site_id,
            ev_charging_session_id=row.ev_charging_session_id,
            connected_at=row.connected_at,
            disconnected_at=row.disconnected_at,
            charging_started_at=row.charging_started_at,
            charging_stopped_at=row.charging_stopped_at,
            start_soc=row.start_soc,
            end_soc=row.end_soc,
            target_soc=row.target_soc,
            status=row.status,
            meter_start_kwh=row.meter_start_kwh,
            meter_stop_kwh=row.meter_stop_kwh,
            halo_energy_kwh=row.halo_energy_kwh,
            estimated_battery_energy_delta_kwh=row.estimated_battery_energy_delta_kwh,
            solar_direct_kwh=row.solar_direct_kwh,
            solar_battery_kwh=row.solar_battery_kwh,
            grid_battery_kwh=row.grid_battery_kwh,
            grid_direct_kwh=row.grid_direct_kwh,
            actual_cost_sek=row.actual_cost_sek,
            reference_cost_sek=row.reference_cost_sek,
            savings_sek=row.savings_sek,
            renewable_share_pct=row.renewable_share_pct,
            grid_share_pct=row.grid_share_pct,
            identification_confidence=row.identification_confidence,
            energy_quality=row.energy_quality,
            cost_quality=row.cost_quality,
            attribution_quality=row.attribution_quality,
            savings_baseline=row.savings_baseline,
            calculation_version=row.calculation_version,
            reconciliation_delta_kwh=row.reconciliation_delta_kwh,
            reconciliation_note=row.reconciliation_note,
            latitude=row.latitude,
            longitude=row.longitude,
            location_id=row.location_id,
            location_name=row.location_name,
            charger_operator=row.charger_operator,
            charger_network=row.charger_network,
            charging_type=row.charging_type,
            connector_type=row.connector_type,
            home_charging=row.home_charging,
            energy_source=row.energy_source,
            estimated_energy_kwh=row.estimated_energy_kwh,
            charging_power_avg_kw=row.charging_power_avg_kw,
            charging_power_max_kw=row.charging_power_max_kw,
            charging_cost_sek=row.charging_cost_sek,
            cost_source=row.cost_source,
            detection_confidence=row.detection_confidence,
            identification_method=row.identification_method,
            vehicle_data_quality=row.vehicle_data_quality,
            charging_state=row.charging_state,
        )
