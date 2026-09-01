"""Knowledge base wrapper for geofences, observations, and confirmed stations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.charging_location_repo import ChargingLocationRepository
from energy_core.db.charging_station_repo import ChargingStationRecord, ChargingStationRepository
from energy_core.vehicles.charging_intelligence.location import (
    ChargingLocationDefinition,
    ChargingLocationResolver,
    LocationClassification,
)


@dataclass(frozen=True, slots=True)
class KnownLocationMatch:
    location: ChargingLocationDefinition
    distance_m: float


class ChargingLocationKnowledgeBase:
    def __init__(
        self,
        session: AsyncSession,
        *,
        site_id: int,
        locations: list[ChargingLocationDefinition] | None = None,
    ) -> None:
        self._session = session
        self._site_id = site_id
        self._location_repo = ChargingLocationRepository(session)
        self._station_repo = ChargingStationRepository(session)
        self._locations = locations or []
        self._resolver = ChargingLocationResolver(self._locations)

    def set_locations(self, locations: list[ChargingLocationDefinition]) -> None:
        self._locations = locations
        self._resolver = ChargingLocationResolver(locations)

    @property
    def location_resolver(self) -> ChargingLocationResolver:
        return self._resolver

    def find_known_location(self, lat: float, lon: float) -> KnownLocationMatch | None:
        best: ChargingLocationDefinition | None = None
        best_distance = float("inf")
        for location in self._locations:
            from energy_core.vehicles.charging_intelligence.location import haversine_m

            distance = haversine_m(lat, lon, location.latitude, location.longitude)
            if distance <= location.radius_m and distance < best_distance:
                best = location
                best_distance = distance
        if best is None:
            return None
        return KnownLocationMatch(location=best, distance_m=best_distance)

    async def find_confirmed_station_near(
        self,
        lat: float,
        lon: float,
        *,
        radius_m: float,
    ) -> list[ChargingStationRecord]:
        return await self._station_repo.find_confirmed_near(
            latitude=lat,
            longitude=lon,
            radius_m=radius_m,
        )

    async def record_usage(self, station_id: int) -> None:
        await self._station_repo.record_usage(station_id)

    async def confirm_station(self, **kwargs) -> ChargingStationRecord:
        return await self._station_repo.confirm_station(**kwargs)

    def is_home(self, location: ChargingLocationDefinition | None) -> bool:
        if location is None:
            return False
        return location.classification in {
            LocationClassification.HOME,
            LocationClassification.HOME_SECONDARY,
        }
