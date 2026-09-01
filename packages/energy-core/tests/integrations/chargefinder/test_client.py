"""Tests for ChargeFinder HTTP client."""

from __future__ import annotations

import json
import zlib
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from energy_core.integrations.charging_stations.chargefinder.http_client import ChargeFinderHttpLookupClient
from energy_core.integrations.charging_stations.exceptions import ChargeFinderBlockedError


def _encrypted_payload(key_hex: str, data: list) -> dict:
    key = key_hex.encode("ascii")
    raw = json.dumps(data).encode("utf-8")
    compressed = zlib.compress(raw)
    aes = AESGCM(key)
    iv = b"\x00" * 12
    ct = aes.encrypt(iv, compressed, None)
    return {"i": iv.hex(), "e": ct[:-16].hex(), "a": ct[-16:].hex()}


@pytest.mark.asyncio
async def test_search_near_parses_encrypted_response():
    key_hex = "9ac6af64f912e44291c7989bb7da774a"
    stations = [{"slug": "abc123", "title": "Test", "location": {"latitude": 55.6761, "longitude": 12.5683}}]
    payload = _encrypted_payload(key_hex, stations)

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        get = AsyncMock(return_value=FakeResponse())

    with patch(
        "energy_core.integrations.charging_stations.chargefinder.http_client.extract_aes_key_hex",
        return_value=key_hex,
    ):
        with patch("energy_core.integrations.charging_stations.chargefinder.http_client.httpx.AsyncClient", return_value=FakeClient()):
            client = ChargeFinderHttpLookupClient()
            result, latency_ms, status = await client.search_near(latitude=55.6761, longitude=12.5683, radius_m=150)

    assert status == 200
    assert latency_ms >= 0
    assert result[0]["slug"] == "abc123"


@pytest.mark.asyncio
async def test_search_near_http_403_raises_blocked():
    class FakeResponse:
        status_code = 403

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        get = AsyncMock(return_value=FakeResponse())

    with patch("energy_core.integrations.charging_stations.chargefinder.http_client.httpx.AsyncClient", return_value=FakeClient()):
        client = ChargeFinderHttpLookupClient(cooldown_seconds=60)
        with pytest.raises(ChargeFinderBlockedError):
            await client.search_near(latitude=55.6761, longitude=12.5683, radius_m=150)
