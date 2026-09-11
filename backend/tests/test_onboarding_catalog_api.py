"""Onboarding catalog API tests."""

import pytest


@pytest.mark.asyncio
async def test_onboarding_catalog_lists_categories(client):
    ac, _, _ = client
    res = await ac.get("/api/system/onboarding-catalog")
    assert res.status_code == 200
    body = res.json()
    category_ids = {item["id"] for item in body["categories"]}
    assert "ev_charger" in category_ids
    assert "vehicle" in category_ids


@pytest.mark.asyncio
async def test_onboarding_catalog_includes_chargeamps(client):
    ac, _, _ = client
    res = await ac.get("/api/system/onboarding-catalog")
    modules = res.json()["modules_by_category"]["ev_charger"]
    module_ids = {item["module_id"] for item in modules}
    assert "integration.chargeamps" in module_ids
    chargeamps = next(item for item in modules if item["module_id"] == "integration.chargeamps")
    assert chargeamps["onboardable"] is True
    assert chargeamps["configuration_schema"]["fields"]


@pytest.mark.asyncio
async def test_system_modules_includes_onboarding_metadata(client):
    ac, _, _ = client
    res = await ac.get("/api/system/modules")
    assert res.status_code == 200
    heartbeat = next(
        item for item in res.json()["modules"] if item["module_id"] == "integration.heartbeat"
    )
    assert heartbeat["onboardable"] is True
    assert heartbeat["configuration_schema"]
