"""Charging location persistence and seeding."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import ChargingLocationModel, ChargingLocationObservationModel, SiteModel
from energy_core.vehicles.charging_intelligence.location import (
    ChargingLocationDefinition,
    LocationClassification,
)


class ChargingLocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_site(self, site_id: int) -> list[ChargingLocationDefinition]:
        rows = await self._session.scalars(
            select(ChargingLocationModel)
            .where(ChargingLocationModel.site_id == site_id, ChargingLocationModel.enabled.is_(True))
            .order_by(ChargingLocationModel.name)
        )
        return [_to_definition(row) for row in rows]

    async def seed_home_from_site_config(self, site: SiteModel) -> ChargingLocationModel | None:
        existing = await self._session.scalar(
            select(ChargingLocationModel).where(
                ChargingLocationModel.site_id == site.id,
                ChargingLocationModel.classification == LocationClassification.HOME.value,
            )
        )
        if existing is not None:
            return existing
        lat = getattr(site, "latitude", None)
        lon = getattr(site, "longitude", None)
        if lat is None or lon is None:
            from energy_core.db.models import SolarSiteConfigurationModel

            config = await self._session.scalar(
                select(SolarSiteConfigurationModel).where(SolarSiteConfigurationModel.site_id == site.id)
            )
            if config is not None:
                lat = config.latitude
                lon = config.longitude
        if lat is None or lon is None:
            return None
        row = ChargingLocationModel(
            site_id=site.id,
            name="Home Åkarp",
            classification=LocationClassification.HOME.value,
            latitude=lat,
            longitude=lon,
            radius_m=100,
            expected_operator="Charge Amps Halo",
            expected_charging_type="AC",
            price_model="FREE",
            enabled=True,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def record_observation(
        self,
        *,
        site_id: int,
        latitude: float,
        longitude: float,
        radius_m: int,
        location_name: str,
        charger_operator: str | None,
        charging_type: str | None,
    ) -> None:
        now = datetime.now(UTC)
        row = await self._session.scalar(
            select(ChargingLocationObservationModel).where(
                ChargingLocationObservationModel.site_id == site_id,
                ChargingLocationObservationModel.location_name == location_name,
            )
        )
        if row is None:
            self._session.add(
                ChargingLocationObservationModel(
                    site_id=site_id,
                    latitude=latitude,
                    longitude=longitude,
                    radius_m=radius_m,
                    location_name=location_name,
                    charger_operator=charger_operator,
                    charging_type=charging_type,
                    hit_count=1,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.hit_count += 1
            row.latitude = latitude
            row.longitude = longitude
            row.radius_m = radius_m
            row.charger_operator = charger_operator
            row.charging_type = charging_type
            row.updated_at = now
        await self._session.flush()


def _to_definition(row: ChargingLocationModel) -> ChargingLocationDefinition:
    return ChargingLocationDefinition(
        id=row.id,
        name=row.name,
        classification=LocationClassification(row.classification),
        latitude=row.latitude,
        longitude=row.longitude,
        radius_m=row.radius_m,
        expected_operator=row.expected_operator,
        expected_network=row.expected_network,
        expected_charging_type=row.expected_charging_type,
        charger_id=row.charger_id,
        price_model=row.price_model,
        price_value=row.price_value,
    )
