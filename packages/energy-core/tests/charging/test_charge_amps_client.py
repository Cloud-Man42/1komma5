"""Tests for Charge Amps client and error handling."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from energy_core.chargers.client import ChargeAmpsClient, sanitize_error_message
from energy_core.chargers.errors import ChargerApiError


def test_sanitize_error_message_redacts_secrets():
    message = "Authorization Bearer abc123 failed for apiKey=secret"
    sanitized = sanitize_error_message(message)
    assert "abc123" not in sanitized
    assert "secret" not in sanitized


@pytest.mark.asyncio
async def test_client_auth_failure_raises_auth_error():
    client = ChargeAmpsClient(
        charger_id="2106037142M",
        api_key="valid-key",
        email="user@example.com",
        password="secret",
    )
    response = httpx.Response(401, request=httpx.Request("POST", "https://eapi.charge.space/api/v5/auth/login"))
    with patch("energy_core.chargers.client.httpx.AsyncClient") as client_cls:
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.__aexit__.return_value = None
        http.post = AsyncMock(return_value=response)
        client_cls.return_value = http

        with pytest.raises(ChargerApiError) as exc:
            await client._ensure_token()
        assert exc.value.code == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_client_rate_limit_retries():
    client = ChargeAmpsClient(
        charger_id="2106037142M",
        api_key="valid-key",
        email="user@example.com",
        password="secret",
    )
    client._token = "token"
    rate_limited = httpx.Response(
        429,
        headers={"Retry-After": "0"},
        request=httpx.Request("GET", "https://eapi.charge.space/api/v5/chargepoints/2106037142M/status"),
    )
    ok = httpx.Response(
        200,
        json={"connectorStatuses": [{"connectorId": 1, "status": "Available"}]},
        request=httpx.Request("GET", "https://eapi.charge.space/api/v5/chargepoints/2106037142M/status"),
    )

    with patch("energy_core.chargers.client.httpx.AsyncClient") as client_cls:
        http = AsyncMock()
        http.__aenter__.return_value = http
        http.__aexit__.return_value = None
        http.request = AsyncMock(side_effect=[rate_limited, ok])
        client_cls.return_value = http

        data = await client.get_chargepoint_status(force=True)
        assert data["connectorStatuses"][0]["status"] == "Available"


@pytest.mark.asyncio
async def test_client_status_cache_avoids_repeat_calls():
    client = ChargeAmpsClient(
        charger_id="2106037142M",
        api_key="valid-key",
        email="user@example.com",
        password="secret",
    )
    client._token = "token"
    request = AsyncMock(
        return_value={
            "connectorStatuses": [{"connectorId": 1, "status": "Charging"}],
        }
    )
    with patch.object(client, "_request", request):
        first = await client.get_chargepoint_status(force=True)
        second = await client.get_chargepoint_status()
        assert first == second
        request.assert_awaited_once()
