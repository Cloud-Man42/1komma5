"""Tests for HeartBeat client optional endpoints."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from energy_core.heartbeat_client import HeartbeatClient, HeartbeatCredentials


@pytest.mark.asyncio
async def test_fetch_optimizations_returns_empty_on_400():
    client = HeartbeatClient(HeartbeatCredentials(api_url="https://example.com", api_token="token"))
    request = httpx.Request("GET", "https://example.com/v1/heartbeat-ai/optimizations")
    response = httpx.Response(400, request=request)
    with patch.object(
        client,
        "_request",
        AsyncMock(
            side_effect=httpx.HTTPStatusError("bad request", request=request, response=response),
        ),
    ):
        items = await client.fetch_optimizations(
            "system-id",
            from_iso="2026-08-14T00:00:00Z",
            to_iso="2026-08-15T00:00:00Z",
        )
    assert items == []


@pytest.mark.asyncio
async def test_update_ev_charge_settings_patches_payload():
    client = HeartbeatClient(HeartbeatCredentials(api_url="https://example.com", api_token="token"))
    with patch.object(
        client,
        "patch_ev",
        AsyncMock(return_value={"id": "ev-1"}),
    ) as patch_ev:
        await client.update_ev_charge_settings(
            "system-id",
            "ev-1",
            charging_mode="SMART_CHARGE",
            target_soc_pct=80.0,
            departure_time="07:00",
        )
    patch_ev.assert_awaited_once_with(
        "system-id",
        "ev-1",
        {
            "chargeSettings": {
                "chargingMode": "SMART_CHARGE",
                "targetSoc": 0.8,
                "primaryScheduleDepartureTime": "07:00",
            }
        },
    )
