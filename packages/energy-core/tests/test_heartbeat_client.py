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
