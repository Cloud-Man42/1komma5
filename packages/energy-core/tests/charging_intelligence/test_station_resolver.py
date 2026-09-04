"""Tests for ChargingStationResolver."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from energy_core.integrations.charging_stations.models import (
    ChargingStationCandidate,
    StationProvider,
    StationResolutionStatus,
)
from energy_core.vehicles.charging_intelligence.knowledge_base import ChargingLocationKnowledgeBase
from energy_core.vehicles.charging_intelligence.location import (
    ChargingLocationDefinition,
    IdentificationMethod,
    LocationClassification,
)
from energy_core.vehicles.charging_intelligence.station_resolver import (
    ChargingStationResolver,
    VehicleResolutionContext,
)


class FakeProvider:
    enabled = True

    def __init__(self, candidates: list[ChargingStationCandidate] | None = None) -> None:
        self._candidates = candidates or []
        self.find_stations = AsyncMock(return_value=self._candidates)


class FakeCache:
    def __init__(self) -> None:
        self._data = {}

    async def get(self, **kwargs):
        return self._data.get((kwargs["latitude"], kwargs["longitude"], kwargs["radius_m"]))

    async def put(self, **kwargs):
        self._data[(kwargs["latitude"], kwargs["longitude"], kwargs["radius_m"])] = kwargs["resolved"]


class FakeKB(ChargingLocationKnowledgeBase):
    def __init__(self, locations):
        self._locations = locations
        self._resolver = __import__(
            "energy_core.vehicles.charging_intelligence.location",
            fromlist=["ChargingLocationResolver"],
        ).ChargingLocationResolver(locations)

    @property
    def location_resolver(self):
        return self._resolver

    def find_known_location(self, lat, lon):
        for loc in self._locations:
            from energy_core.vehicles.charging_intelligence.location import haversine_m

            d = haversine_m(lat, lon, loc.latitude, loc.longitude)
            if d <= loc.radius_m:
                from energy_core.vehicles.charging_intelligence.knowledge_base import KnownLocationMatch

                return KnownLocationMatch(location=loc, distance_m=d)
        return None

    def is_home(self, location):
        return location.classification == LocationClassification.HOME

    async def find_confirmed_station_near(self, *args, **kwargs):
        return []


@pytest.mark.asyncio
async def test_home_halo_skips_chargefinder():
    home = ChargingLocationDefinition(
        id=1,
        name="Home Åkarp",
        classification=LocationClassification.HOME,
        latitude=55.605,
        longitude=13.0038,
        radius_m=100,
        expected_operator="Charge Amps Halo",
        expected_charging_type="AC",
    )
    provider = FakeProvider(
        [ChargingStationCandidate(
            provider=StationProvider.CHARGEFINDER,
            provider_station_id="X",
            operator="Other",
            station_name="Public",
            latitude=55.605,
            longitude=13.0038,
            distance_m=10,
        )]
    )
    resolver = ChargingStationResolver(provider)
    kb = FakeKB([home])
    result = await resolver.resolve(
        55.605,
        13.0038,
        knowledge_base=kb,
        vehicle_state=VehicleResolutionContext(mercedes_charging=True, halo_charger_active=True),
    )
    assert result.identification_method == IdentificationMethod.VEHICLE_AND_CHARGER_CORRELATION.value
    provider.find_stations.assert_not_called()


@pytest.mark.asyncio
async def test_no_gps_returns_unknown():
    resolver = ChargingStationResolver(FakeProvider())
    kb = FakeKB([])
    result = await resolver.resolve(None, None, knowledge_base=kb)
    assert result.station_resolution_status == StationResolutionStatus.UNKNOWN


@pytest.mark.asyncio
async def test_cache_hit_skips_provider():
    from energy_core.integrations.charging_stations.models import ResolvedChargingLocation

    provider = FakeProvider()
    cache = FakeCache()
    cached = ResolvedChargingLocation(
        location_name="Cached",
        station_name="Cached",
        operator_name="Op",
        charging_type="AC",
        connector_type=None,
        max_power_kw=22,
        distance_meters=10,
        confidence=80,
        confidence_band="HIGH",
        identification_method="CHARGEFINDER",
        source="CACHE",
        station_resolution_status=StationResolutionStatus.OK,
        price_model="PER_KWH",
        price_value_sek_kwh=4.5,
    )
    await cache.put(latitude=57.26, longitude=16.48, radius_m=150, resolved=cached, ttl_seconds=3600)
    resolver = ChargingStationResolver(provider, cache_repo=cache)
    kb = FakeKB([])
    result = await resolver.resolve(57.26, 16.48, knowledge_base=kb)
    assert result.location_name == "Cached"
    provider.find_stations.assert_not_called()


@pytest.mark.asyncio
async def test_disabled_provider_degraded_geofence():
    provider = FakeProvider()
    provider.enabled = False
    hotel = ChargingLocationDefinition(
        id=2,
        name="Hotel",
        classification=LocationClassification.HOTEL,
        latitude=59.3293,
        longitude=18.0686,
        radius_m=150,
        expected_operator="ChargeNode",
    )
    resolver = ChargingStationResolver(provider)
    kb = FakeKB([hotel])
    result = await resolver.resolve(59.3293, 18.0686, knowledge_base=kb)
    assert result.station_resolution_status == StationResolutionStatus.DEGRADED
    assert result.location_name == "Hotel"
