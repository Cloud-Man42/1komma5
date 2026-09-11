"""Site devices API tests."""

import pytest


@pytest.mark.asyncio
async def test_site_devices_404_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/no-such-site/devices")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_site_devices_lists_registry_projection(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/devices")
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "akarp"
    assert isinstance(body["devices"], list)
    if body["devices"]:
        device = body["devices"][0]
        assert "device_type" in device
        assert "health_status" in device
        assert device["health_status"] in {"healthy", "degraded", "unavailable", "disabled"}


@pytest.mark.asyncio
async def test_site_device_detail(client):
    ac, _, _ = client
    listing = await ac.get("/api/sites/akarp/devices")
    assert listing.status_code == 200
    devices = listing.json()["devices"]
    if not devices:
        pytest.skip("No devices seeded for akarp")
    device = devices[0]
    res = await ac.get(f"/api/sites/akarp/devices/{device['device_type']}/{device['device_id']}")
    assert res.status_code == 200
    body = res.json()
    assert body["device_id"] == device["device_id"]
    assert body["configuration_status"] in {"active", "disabled", "unknown"}


@pytest.mark.asyncio
async def test_site_device_detail_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/devices/ev_charger/999999")
    assert res.status_code == 404
