"""API tests for energy control routes."""

import pytest
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.types import OptimizationMode


@pytest.mark.asyncio
async def test_energy_control_status_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/energy-control/status")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_energy_control_status_defaults(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/energy-control/status")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == "akarp"
    assert data["optimization_mode"] == "MONITOR_ONLY"
    assert data["control_enabled"] is False
    assert data["provider"] == "noop-dry-run"


@pytest.mark.asyncio
async def test_energy_control_update_mode(client):
    ac, session_factory, _ = client
    res = await ac.put(
        "/api/sites/akarp/energy-control/settings",
        json={"optimization_mode": "RECOMMEND"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["optimization_mode"] == "RECOMMEND"

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        assert site.optimization_mode == OptimizationMode.RECOMMEND.value


@pytest.mark.asyncio
async def test_energy_control_update_invalid_mode(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/energy-control/settings",
        json={"optimization_mode": "INVALID"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_energy_control_preview_skipped_in_monitor(client):
    ac, _, _ = client
    res = await ac.post(
        "/api/sites/akarp/energy-control/preview",
        json={"action": "USE_NOW"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "SKIPPED"
    assert data["dry_run"] is True


@pytest.mark.asyncio
async def test_energy_control_preview_in_recommend(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/energy-control/settings",
        json={"optimization_mode": "RECOMMEND"},
    )
    res = await ac.post(
        "/api/sites/akarp/energy-control/preview",
        json={"action": "STORE_IN_BATTERY"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "PREVIEW"
    assert data["action"] == "STORE_IN_BATTERY"


@pytest.mark.asyncio
async def test_energy_control_apply_rejected_without_flag(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/energy-control/settings",
        json={"optimization_mode": "SEMI_AUTOMATIC"},
    )
    res = await ac.post(
        "/api/sites/akarp/energy-control/apply",
        json={"action": "USE_NOW"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "REJECTED"


@pytest.mark.asyncio
async def test_energy_control_apply_when_enabled(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/energy-control/settings",
        json={"optimization_mode": "SEMI_AUTOMATIC", "control_enabled": True},
    )
    res = await ac.post(
        "/api/sites/akarp/energy-control/apply",
        json={"action": "USE_NOW"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "APPLIED"
    assert data["dry_run"] is False

    recent = await ac.get("/api/sites/akarp/energy-control/recent?limit=5")
    assert recent.status_code == 200
    assert len(recent.json()["actions"]) >= 1
