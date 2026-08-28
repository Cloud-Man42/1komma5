"""Spa smart control API tests."""

import pytest


@pytest.mark.asyncio
async def test_spa_control_config_get_and_put(client):
    ac, _, _ = client

    res = await ac.get("/api/sites/akarp/spa/control/config")
    assert res.status_code == 200
    body = res.json()
    assert body["strategy"] == "SMART"
    assert body["dry_run"] is True
    assert body["filter_cycles_per_day"] == 4
    assert body["filter_duration_minutes"] == 120

    updated = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"smart_control_enabled": True, "strategy": "CHEAPEST", "dry_run": True},
    )
    assert updated.status_code == 200
    assert updated.json()["smart_control_enabled"] is True
    assert updated.json()["strategy"] == "CHEAPEST"


@pytest.mark.asyncio
async def test_spa_control_config_update_temperature_celsius(client):
    ac, _, _ = client

    updated = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={
            "smart_preheat_enabled": True,
            "normal_temperature_c": 38.5,
            "max_preheat_temperature_c": 39.5,
            "min_comfort_temperature_c": 37.5,
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["smart_preheat_enabled"] is True
    assert body["normal_temperature_c"] == 38.5
    assert body["max_preheat_temperature_c"] == 39.5
    assert body["min_comfort_temperature_c"] == 37.5


@pytest.mark.asyncio
async def test_spa_control_config_invalid_temperature_422(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"normal_temperature_c": 50},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_spa_control_config_update_filter_cycles(client):
    ac, _, _ = client
    updated = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"filter_cycles_per_day": 2, "filter_duration_minutes": 120},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["filter_cycles_per_day"] == 2
    assert body["max_starts_per_day"] == 2
    assert body["min_cleaning_hours_per_day"] == 4


@pytest.mark.asyncio
async def test_spa_plan_includes_daily_windows(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={
            "smart_control_enabled": True,
            "dry_run": True,
            "filter_cycles_per_day": 2,
            "filter_duration_minutes": 120,
        },
    )
    res = await ac.get("/api/sites/akarp/spa/plan")
    assert res.status_code == 200
    body = res.json()
    assert body["daily_target_hours"] == 4
    assert body["config_summary_sv"] is not None
    assert "daily_windows" in body
    assert body["filter_control_source_sv"] == "Arctic Spa"
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"strategy": "INVALID"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_spa_control_config_404_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/spa/control/config")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_spa_plan_disabled_by_default(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/plan")
    assert res.status_code == 200
    assert res.json()["enabled"] is False


@pytest.mark.asyncio
async def test_spa_plan_enabled_after_config(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"smart_control_enabled": True, "dry_run": True},
    )
    res = await ac.get("/api/sites/akarp/spa/plan")
    assert res.status_code == 200
    body = res.json()
    assert body["enabled"] is True
    assert body["cycles_planned"] is not None or body["daily_windows"] is not None


@pytest.mark.asyncio
async def test_spa_timeline(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/timeline")
    assert res.status_code == 200
    assert "entries" in res.json()


@pytest.mark.asyncio
async def test_spa_events(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/events")
    assert res.status_code == 200
    assert "events" in res.json()


@pytest.mark.asyncio
async def test_spa_economics_invalid_period_422(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/economics?period=invalid")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_spa_economics_today(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/economics?period=today")
    assert res.status_code == 200
    assert res.json()["period"] == "today"


@pytest.mark.asyncio
async def test_spa_run_cleaning_now_requires_smart_control(client):
    ac, _, _ = client
    res = await ac.post("/api/sites/akarp/spa/cleaning/run-now")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_spa_run_cleaning_now_success(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"smart_control_enabled": True, "dry_run": True},
    )
    res = await ac.post("/api/sites/akarp/spa/cleaning/run-now")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["dry_run"] is True
    assert "test" in body["message"].lower()


@pytest.mark.asyncio
async def test_spa_run_cleaning_now_shadow_mode_allows_manual(client):
    ac, _, _ = client
    await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"smart_control_enabled": True, "dry_run": False, "shadow_mode": True},
    )
    res = await ac.post("/api/sites/akarp/spa/cleaning/run-now")
    assert res.status_code == 200
    body = res.json()
    assert body["dry_run"] is False


@pytest.mark.asyncio
async def test_spa_control_config_toggle_shadow_mode(client):
    ac, _, _ = client
    enabled = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"shadow_mode": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["shadow_mode"] is True

    disabled = await ac.put(
        "/api/sites/akarp/spa/control/config",
        json={"shadow_mode": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["shadow_mode"] is False


@pytest.mark.asyncio
async def test_spa_shadow(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/spa/shadow")
    assert res.status_code == 200
    body = res.json()
    assert "total_actual_cost_sek" in body
