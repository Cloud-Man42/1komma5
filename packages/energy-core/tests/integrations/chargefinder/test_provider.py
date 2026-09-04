"""Tests for ChargeFinder provider pricing enrichment."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from energy_core.integrations.charging_stations.chargefinder.provider import (
    ChargeFinderChargingStationProvider,
    ChargeFinderMode,
)
from energy_core.integrations.charging_stations.models import ChargingStationCandidate, DataQuality, StationProvider


def _candidate(**overrides) -> ChargingStationCandidate:
    base = ChargingStationCandidate(
        provider=StationProvider.CHARGEFINDER,
        provider_station_id="yrj6mm",
        operator="ChargeNode",
        station_name="Hotell Corallen",
        latitude=57.261,
        longitude=16.481,
        price_model="UNKNOWN",
        price_value_sek_kwh=None,
        data_quality=DataQuality.LIVE,
    )
    return replace(base, **overrides) if overrides else base


@pytest.mark.asyncio
async def test_enrich_missing_pricing_uses_status_tariffs():
    lookup_client = AsyncMock()
    lookup_client.fetch_station.return_value = (
        {
            "slug": "yrj6mm",
            "title": "Hotell Corallen",
            "operator": "ChargeNode",
            "location": {"latitude": 57.261, "longitude": 16.481},
            "freeCharging": 0,
            "realtimeId": "99n5kkhpwr9n8",
            "outletList": [{"costKwh": 0, "outlets": []}],
        },
        10,
        200,
    )
    lookup_client.fetch_status.return_value = (
        [{"id": "SE*CNE*E4336", "tariffs": [{"currency": "SEK", "costKwh": 4.5}]}],
        12,
        200,
    )
    provider = ChargeFinderChargingStationProvider(mode=ChargeFinderMode.WEB, lookup_client=lookup_client)

    enriched = await provider._enrich_missing_pricing(
        [_candidate()],
        vehicle_lat=57.261,
        vehicle_lon=16.481,
    )

    assert len(enriched) == 1
    assert enriched[0].price_model == "PER_KWH"
    assert enriched[0].price_value_sek_kwh == 4.5
    lookup_client.fetch_status.assert_awaited_once_with(realtime_id="99n5kkhpwr9n8")


@pytest.mark.asyncio
async def test_enrich_missing_pricing_does_not_mark_zero_kwh_as_free():
    lookup_client = AsyncMock()
    lookup_client.fetch_station.return_value = (
        {
            "slug": "yrj6mm",
            "title": "Hotell Corallen",
            "operator": "ChargeNode",
            "location": {"latitude": 57.261, "longitude": 16.481},
            "freeCharging": 0,
            "outletList": [{"costKwh": 0, "outlets": []}],
        },
        10,
        200,
    )
    provider = ChargeFinderChargingStationProvider(mode=ChargeFinderMode.WEB, lookup_client=lookup_client)

    enriched = await provider._enrich_missing_pricing(
        [_candidate()],
        vehicle_lat=57.261,
        vehicle_lon=16.481,
    )

    assert len(enriched) == 1
    assert enriched[0].price_model == "UNKNOWN"
    lookup_client.fetch_status.assert_not_called()
