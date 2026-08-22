"""Spa API route tests."""

import pytest


@pytest.mark.asyncio
async def test_spa_status_and_config(client):
    ac, _, _ = client

    status = await ac.get("/api/sites/akarp/spa/status")
    assert status.status_code == 200
    body = status.json()
    assert body["site_slug"] == "akarp"
    assert body["integration_enabled"] is False

    config = await ac.get("/api/sites/akarp/spa/config")
    assert config.status_code == 200
    assert config.json()["poll_interval_seconds"] == 60

    updated = await ac.put(
        "/api/sites/akarp/spa/config",
        json={"integration_enabled": True, "api_base_url": "https://api.myarcticspa.com"},
    )
    assert updated.status_code == 200
    assert updated.json()["integration_enabled"] is True

    today = await ac.get("/api/sites/akarp/spa/energy/today")
    assert today.status_code == 200
    assert today.json()["has_data"] is False

    health = await ac.get("/api/sites/akarp/spa/health")
    assert health.status_code == 200

    readiness = await ac.get("/api/system/integrations/spa-readiness")
    assert readiness.status_code == 200
