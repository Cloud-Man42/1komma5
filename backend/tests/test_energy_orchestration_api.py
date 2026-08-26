"""API tests for site energy orchestration."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_orchestration_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/missing/energy/orchestration")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_orchestration_empty_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/energy/orchestration")
    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    assert isinstance(body["loads"], list)


@pytest.mark.asyncio
async def test_orchestration_priorities_validation(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/energy/orchestration/priorities",
        json={"loads": []},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_orchestration_priorities_unknown_load(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/energy/orchestration/priorities",
        json={"loads": [{"load_id": "unknown_load", "priority": 50}]},
    )
    assert res.status_code == 422
