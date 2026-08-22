"""Tests for OneKommaFiveHeartbeatProvider."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from energy_core.providers.onekommafive import (
    HeartbeatRuntimeConfig,
    OneKommaFiveHeartbeatProvider,
    SiteRuntimeInfo,
)


def _runtime(**kwargs) -> HeartbeatRuntimeConfig:
    defaults = {
        "connection_type": "cloud",
        "api_url": "https://heartbeat.1komma5grad.com/api",
        "username": "user@example.com",
        "password": "secret",
        "api_token": "token",
        "site_system_ids": {"akarp": "00000000-0000-0000-0000-000000000001"},
        "site_info": {
            "akarp": SiteRuntimeInfo(name="Åkarp", timezone="Europe/Stockholm"),
        },
    }
    defaults.update(kwargs)
    return HeartbeatRuntimeConfig(**defaults)


@pytest.mark.asyncio
async def test_onekommafive_provider_returns_empty_without_credentials():
    provider = OneKommaFiveHeartbeatProvider(
        _runtime(username="", password="", api_token="")
    )
    readings = await provider.fetch_readings()
    assert readings == []


@pytest.mark.asyncio
async def test_onekommafive_provider_list_sites_uses_metadata():
    provider = OneKommaFiveHeartbeatProvider(_runtime())
    sites = await provider.list_sites()
    assert len(sites) == 1
    assert sites[0].slug == "akarp"
    assert sites[0].name == "Åkarp"
    assert sites[0].timezone == "Europe/Stockholm"


@pytest.mark.asyncio
async def test_onekommafive_provider_fetch_readings_success():
    overview = {
        "timestamp": "2026-08-13T18:00:00Z",
        "liveHeroView": {
            "production": {"value": 3200},
            "consumption": {"value": 1800},
            "gridConsumption": {"value": 100},
            "gridFeedIn": {"value": 0},
            "totalStateOfCharge": 0.65,
        },
        "summaryCards": {"battery": {"power": {"value": -200}}},
    }
    provider = OneKommaFiveHeartbeatProvider(_runtime())
    with patch.object(
        provider,
        "_build_client",
        return_value=AsyncMock(fetch_live_overview=AsyncMock(return_value=overview)),
    ):
        readings = await provider.fetch_readings()

    assert len(readings) == 1
    assert readings[0].site_slug == "akarp"
    assert readings[0].solar_production_w == 3200
    assert readings[0].consumption_w == 1800
    assert readings[0].battery_soc_pct == 65


@pytest.mark.asyncio
async def test_onekommafive_provider_skips_failed_site():
    overview = {
        "timestamp": "2026-08-13T18:00:00Z",
        "liveHeroView": {"production": {"value": 1000}, "consumption": {"value": 500}},
    }
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(404, request=request)
    client = AsyncMock()
    client.fetch_live_overview = AsyncMock(
        side_effect=[
            httpx.HTTPStatusError("not found", request=request, response=response),
            overview,
        ]
    )
    provider = OneKommaFiveHeartbeatProvider(
        _runtime(
            site_system_ids={
                "summer-house-denmark": "00000000-0000-0000-0000-000000000002",
                "akarp": "00000000-0000-0000-0000-000000000001",
            }
        )
    )
    with patch.object(provider, "_build_client", return_value=client):
        readings = await provider.fetch_readings()

    assert len(readings) == 1
    assert readings[0].site_slug == "akarp"
