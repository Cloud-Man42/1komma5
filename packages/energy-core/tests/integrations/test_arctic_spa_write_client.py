"""Tests for Arctic Spa write client methods."""

import pytest

from energy_core.integrations.arctic_spa.client import ArcticSpaClient
from energy_core.integrations.arctic_spa.models import celsius_to_fahrenheit_int


@pytest.mark.asyncio
async def test_set_filter_sends_on_state():
    client = ArcticSpaClient(base_url="https://api.example.com", api_key="key")
    captured: dict = {}

    async def fake_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json_body"] = kwargs.get("json_body")
        return {}

    client._request = fake_request  # type: ignore[method-assign]
    await client.set_filter(state="on")
    assert captured == {"method": "PUT", "path": "/v2/spa/filter", "json_body": {"state": "on"}}


@pytest.mark.asyncio
async def test_set_temperature_c_quantizes_fahrenheit():
    client = ArcticSpaClient(base_url="https://api.example.com", api_key="key")
    captured: dict = {}

    async def fake_request(method, path, **kwargs):
        captured["json_body"] = kwargs.get("json_body")
        return {}

    client._request = fake_request  # type: ignore[method-assign]
    await client.set_temperature_c(38.0)
    assert captured["json_body"]["setpointF"] == celsius_to_fahrenheit_int(38.0)


def test_celsius_to_fahrenheit_int():
    assert celsius_to_fahrenheit_int(38.0) == 100
    assert celsius_to_fahrenheit_int(38.8) == 102
