"""Device registry read projection over existing ORM tables."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.contracts.health import HealthStatus, from_energy_provider_status
from energy_core.db.models import (
    EnergyConsumerModel,
    EvChargerModel,
    IntegrationHealthModel,
    SolarArrayModel,
    VehicleModel,
)


class DeviceType(StrEnum):
    EV_CHARGER = "ev_charger"
    VEHICLE = "vehicle"
    SOLAR_ARRAY = "solar_array"
    ENERGY_CONSUMER = "energy_consumer"


@dataclass(frozen=True, slots=True)
class DeviceId:
    device_type: DeviceType
    id: int


@dataclass(frozen=True, slots=True)
class DeviceRecord:
    device_id: DeviceId
    site_id: int
    name: str
    manufacturer: str
    model: str
    integration: str | None
    connection_status: str | None
    health_status: HealthStatus
    last_seen: datetime | None
    enabled: bool
    metadata: dict[str, Any] = field(default_factory=dict)


class DeviceRegistry:
    """Read-only projection; no new tables or migrations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_site(self, site_id: int) -> tuple[DeviceRecord, ...]:
        records: list[DeviceRecord] = []
        health_by_provider = await self._health_by_provider(site_id)

        chargers = (
            await self._session.scalars(select(EvChargerModel).where(EvChargerModel.site_id == site_id))
        ).all()
        for charger in chargers:
            records.append(
                DeviceRecord(
                    device_id=DeviceId(DeviceType.EV_CHARGER, charger.id),
                    site_id=site_id,
                    name=charger.name,
                    manufacturer=charger.manufacturer,
                    model=charger.model,
                    integration=charger.integration_method or charger.control_source,
                    connection_status=charger.connection_status,
                    health_status=self._health_for(charger.control_source, health_by_provider),
                    last_seen=charger.last_connection_at or charger.last_heartbeat_data_at,
                    enabled=charger.bridge_enabled,
                    metadata={
                        "external_charger_id": charger.external_charger_id or charger.chargeamp_charger_id,
                    },
                )
            )

        vehicles = (
            await self._session.scalars(select(VehicleModel).where(VehicleModel.site_id == site_id))
        ).all()
        for vehicle in vehicles:
            records.append(
                DeviceRecord(
                    device_id=DeviceId(DeviceType.VEHICLE, vehicle.id),
                    site_id=site_id,
                    name=vehicle.display_name or vehicle.model,
                    manufacturer=vehicle.manufacturer,
                    model=vehicle.model,
                    integration=vehicle.provider,
                    connection_status=None,
                    health_status=self._health_for(vehicle.provider, health_by_provider),
                    last_seen=vehicle.first_seen_at,
                    enabled=vehicle.enabled,
                    metadata={"external_id": vehicle.external_id, "vin": vehicle.vin},
                )
            )

        arrays = (
            await self._session.scalars(select(SolarArrayModel).where(SolarArrayModel.site_id == site_id))
        ).all()
        for array in arrays:
            records.append(
                DeviceRecord(
                    device_id=DeviceId(DeviceType.SOLAR_ARRAY, array.id),
                    site_id=site_id,
                    name=array.name,
                    manufacturer="",
                    model="",
                    integration="heartbeat",
                    connection_status=None,
                    health_status=self._health_for("heartbeat", health_by_provider),
                    last_seen=None,
                    enabled=True,
                    metadata={"capacity_kwp": array.capacity_kwp},
                )
            )

        consumers = (
            await self._session.scalars(
                select(EnergyConsumerModel).where(EnergyConsumerModel.site_id == site_id)
            )
        ).all()
        for consumer in consumers:
            records.append(
                DeviceRecord(
                    device_id=DeviceId(DeviceType.ENERGY_CONSUMER, consumer.id),
                    site_id=site_id,
                    name=consumer.name,
                    manufacturer="",
                    model=consumer.consumer_type,
                    integration=consumer.consumer_type.lower(),
                    connection_status=None,
                    health_status=HealthStatus.HEALTHY if consumer.enabled else HealthStatus.DISABLED,
                    last_seen=consumer.created_at,
                    enabled=consumer.enabled,
                    metadata={"consumer_type": consumer.consumer_type},
                )
            )

        return tuple(records)

    async def _health_by_provider(self, site_id: int) -> dict[str, str]:
        rows = (
            await self._session.scalars(
                select(IntegrationHealthModel).where(IntegrationHealthModel.site_id == site_id)
            )
        ).all()
        return {row.provider: row.status for row in rows}

    @staticmethod
    def _health_for(provider: str | None, health_by_provider: dict[str, str]) -> HealthStatus:
        if not provider:
            return HealthStatus.UNAVAILABLE
        status = health_by_provider.get(provider)
        if status is None:
            return HealthStatus.UNAVAILABLE
        return from_energy_provider_status(status)
