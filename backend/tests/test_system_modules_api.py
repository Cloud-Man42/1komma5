"""System modules API tests."""

import pytest


@pytest.mark.asyncio
async def test_system_modules_lists_registered_modules(client):
    ac, _, _ = client
    res = await ac.get("/api/system/modules")
    assert res.status_code == 200
    body = res.json()
    module_ids = {item["module_id"] for item in body["modules"]}
    assert "feature.smart-charging" in module_ids or "charging" in module_ids
    assert "vehicles" in module_ids or "feature.vehicles" in module_ids
