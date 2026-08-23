"""Tests for Arctic Spa HTTP client."""

import pytest
from energy_core.integrations.arctic_spa.client import ArcticSpaApiError, ArcticSpaClient
from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


@pytest.mark.asyncio
async def test_get_status_uses_api_key_header():
    client = ArcticSpaClient(base_url="https://api.example.com", api_key="secret-key")

    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/v2/spa/status"
        return {
            "connected": True,
            "temperatureF": 100,
            "setpointF": 102,
            "pump1": "low",
            "filter_status": "Filtering",
            "errors": [],
        }

    client._request = fake_request  # type: ignore[method-assign]
    status = await client.get_status()
    assert status.connected is True
    assert status.temperature_c == pytest.approx(37.78, abs=0.01)


@pytest.mark.asyncio
async def test_unauthorized_error_type():
    client = ArcticSpaClient(base_url="https://api.example.com", api_key="bad")

    async def fake_request(method, path, **kwargs):
        raise ArcticSpaApiError("Unauthorized — check API key", status_code=401)

    client._request = fake_request  # type: ignore[method-assign]
    with pytest.raises(ArcticSpaApiError) as exc:
        await client.get_status()
    assert exc.value.status_code == 401


def test_status_heater_from_filtering():
    status = ArcticSpaStatus.from_api(
        {"connected": True, "filter_status": "Filtering", "temperatureF": 98, "setpointF": 100}
    )
    assert status.heater_active is True
