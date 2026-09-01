"""Backend ChargeFinder API tests."""

import pytest


def _patch_settings(monkeypatch, settings):
    monkeypatch.setattr("app.api.chargefinder.get_settings", lambda: settings)


@pytest.mark.asyncio
async def test_chargefinder_status(client):
    ac, _, _ = client
    response = await ac.get("/api/integrations/chargefinder/status")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "WEB"
    assert "health_status" in body


@pytest.mark.asyncio
async def test_chargefinder_test_lookup_disabled_mode(client, monkeypatch):
    ac, _, settings = client
    settings.chargefinder_enabled = False
    _patch_settings(monkeypatch, settings)
    response = await ac.post(
        "/api/integrations/chargefinder/test-lookup",
        json={"latitude": 55.6761, "longitude": 12.5683},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_chargefinder_test_lookup_invalid_radius(client):
    ac, _, _ = client
    response = await ac.post(
        "/api/integrations/chargefinder/test-lookup",
        json={"latitude": 55.6761, "longitude": 12.5683, "radius_m": 999},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chargefinder_raw_lookup_disabled(client, monkeypatch):
    ac, _, settings = client
    settings.chargefinder_enabled = False
    _patch_settings(monkeypatch, settings)
    response = await ac.get(
        "/api/integrations/chargefinder/raw-lookup",
        params={"latitude": 55.6761, "longitude": 12.5683},
    )
    assert response.status_code == 503
