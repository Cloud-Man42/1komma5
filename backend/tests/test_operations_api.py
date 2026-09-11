"""Site operations aggregate API tests."""

import pytest


@pytest.mark.asyncio
async def test_operations_returns_modules_and_devices(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/operations")
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == "akarp"
    assert isinstance(body["modules"], list)
    assert isinstance(body["devices"], list)
    assert "overall_health_status" in body


@pytest.mark.asyncio
async def test_operations_404_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown-site/operations")
    assert res.status_code == 404
