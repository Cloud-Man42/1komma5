from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from helpers import create_charger


@pytest.mark.asyncio
async def test_ev_charger_test_connection_draft(client):
    ac, _, _ = client
    res = await ac.post(
        "/api/sites/akarp/ev-chargers/test-connection",
        json={
            "manufacturer_id": "charge-amps",
            "model_id": "halo",
            "integration_method": "CHARGE_AMPS_CLOUD",
            "chargeamp_charger_id": "mock-halo",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["status"] == "CONNECTED"


@pytest.mark.asyncio
async def test_ev_charger_test_connection_saved(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Test Connection")
    res = await ac.post(f"/api/sites/akarp/ev-chargers/{charger['id']}/test-connection")
    assert res.status_code == 200
    assert res.json()["success"] is True
    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger['id']}")


@pytest.mark.asyncio
async def test_ev_charger_crud(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Halo Åkarp")
    charger_id = charger["id"]

    listing = await ac.get("/api/sites/akarp/ev-chargers")
    assert listing.status_code == 200
    assert any(c["id"] == charger_id for c in listing.json())

    delete = await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_ev_charger_update(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Before Update")
    charger_id = charger["id"]

    res = await ac.put(
        f"/api/sites/akarp/ev-chargers/{charger_id}",
        json={"name": "After Update", "max_current_a": 12},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "After Update"
    assert res.json()["max_current_a"] == 12

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_ev_charger_update_404(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/sites/akarp/ev-chargers/99999",
        json={"name": "Missing"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_ev_charger_sync_requires_heartbeat(client, monkeypatch):
    ac, session_factory, _ = client
    monkeypatch.setattr(
        "energy_core.heartbeat_client_factory.create_heartbeat_client",
        AsyncMock(return_value=None),
    )
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        site.external_system_id = "00000000-0000-0000-0000-000000000001"
        await session.commit()

    res = await ac.post("/api/sites/akarp/ev-chargers/sync")
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_ev_charger_sync_success(client, monkeypatch):
    ac, session_factory, _ = client
    mock_client = SimpleNamespace(
        list_evs=AsyncMock(return_value=[]),
        list_wallboxes=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "energy_core.heartbeat_client_factory.create_heartbeat_client",
        AsyncMock(return_value=mock_client),
    )
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        site.external_system_id = "00000000-0000-0000-0000-000000000001"
        await session.commit()

    res = await ac.post("/api/sites/akarp/ev-chargers/sync")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_ev_charger_listing_includes_live_chargeamps_power(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    meter = SimpleNamespace(get_snapshot=AsyncMock(return_value=SimpleNamespace(power_w=5520.0)))
    monkeypatch.setattr(
        "energy_core.chargers.framework.meter_factory.MeterReaderFactory.from_charger_model",
        lambda *args, **kwargs: meter,
    )
    create = await ac.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Metered Halo",
            "control_source": "chargeamp",
            "chargeamp_charger_id": "halo-metered",
        },
    )

    listing = await ac.get("/api/sites/akarp/ev-chargers")

    charger = next(item for item in listing.json() if item["id"] == create.json()["id"])
    assert charger["power_w"] == 5520.0
    meter.get_snapshot.assert_awaited_once()


@pytest.mark.asyncio
async def test_ev_charger_listing_tolerates_live_power_failure(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    meter = SimpleNamespace(get_snapshot=AsyncMock(side_effect=RuntimeError("unavailable")))
    monkeypatch.setattr(
        "energy_core.chargers.framework.meter_factory.MeterReaderFactory.from_charger_model",
        lambda *args, **kwargs: meter,
    )
    create = await ac.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Unavailable Halo",
            "control_source": "chargeamp",
            "chargeamp_charger_id": "halo-unavailable",
        },
    )

    listing = await ac.get("/api/sites/akarp/ev-chargers")

    charger = next(item for item in listing.json() if item["id"] == create.json()["id"])
    assert charger["power_w"] is None


@pytest.mark.asyncio
async def test_ev_charger_listing_reports_zero_when_meter_is_idle(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    meter = SimpleNamespace(
        get_snapshot=AsyncMock(return_value=SimpleNamespace(power_w=None, is_charging=False)),
    )
    monkeypatch.setattr(
        "energy_core.chargers.framework.meter_factory.MeterReaderFactory.from_charger_model",
        lambda *args, **kwargs: meter,
    )
    create = await ac.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Idle Halo",
            "control_source": "chargeamp",
            "chargeamp_charger_id": "halo-idle",
        },
    )

    listing = await ac.get("/api/sites/akarp/ev-chargers")

    charger = next(item for item in listing.json() if item["id"] == create.json()["id"])
    assert charger["power_w"] == 0.0


@pytest.mark.asyncio
async def test_ev_charger_bridge_status(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Halo Bridge", bridge_enabled=True)
    charger_id = charger["id"]
    assert charger["bridge_enabled"] is True

    status = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/bridge-status")
    assert status.status_code == 200
    data = status.json()
    assert data["charger_id"] == charger_id
    assert data["bridge_enabled"] is True
    assert data["charging_mode"] == "SMART_CHARGE"

    connection = await ac.post(f"/api/sites/akarp/ev-chargers/{charger_id}/test-connection")
    assert connection.status_code == 200
    connection_body = connection.json()
    assert "success" in connection_body
    assert "status" in connection_body

    plan = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/solar-charging-plan")
    assert plan.status_code == 200
    plan_body = plan.json()
    assert plan_body["available"] is False
    assert "energi" in plan_body["explanation_sv"].lower()

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_ev_charger_override_hours(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Override Halo", bridge_enabled=True)
    charger_id = charger["id"]

    override = await ac.post(
        f"/api/sites/akarp/ev-chargers/{charger_id}/override",
        json={"hours": 4},
    )
    assert override.status_code == 200
    body = override.json()
    assert body["override_active"] is True
    assert body["override_until"] is not None

    invalid = await ac.post(
        f"/api/sites/akarp/ev-chargers/{charger_id}/override",
        json={"hours": 6},
    )
    assert invalid.status_code == 422

    cleared = await ac.post(
        f"/api/sites/akarp/ev-chargers/{charger_id}/override",
        json={"clear": True},
    )
    assert cleared.status_code == 200
    assert cleared.json()["override_active"] is False
    assert cleared.json()["override_until"] is None

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_override_from_paused_resumes_quick_charge(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Paused Override Halo", bridge_enabled=True)
    charger_id = charger["id"]

    paused = await ac.patch(
        f"/api/sites/akarp/ev-chargers/{charger_id}/control",
        json={"charging_mode": "PAUSED"},
    )
    assert paused.status_code == 200
    assert paused.json()["charging_mode"] == "PAUSED"

    override = await ac.post(
        f"/api/sites/akarp/ev-chargers/{charger_id}/override",
        json={"hours": 4},
    )
    assert override.status_code == 200
    body = override.json()
    assert body["override_active"] is True
    assert body["charging_mode"] == "QUICK_CHARGE"

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_pause_clears_active_override(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Pause Clears Override", bridge_enabled=True)
    charger_id = charger["id"]

    override = await ac.post(
        f"/api/sites/akarp/ev-chargers/{charger_id}/override",
        json={"hours": 8},
    )
    assert override.status_code == 200
    assert override.json()["override_active"] is True

    paused = await ac.patch(
        f"/api/sites/akarp/ev-chargers/{charger_id}/control",
        json={"charging_mode": "PAUSED"},
    )
    assert paused.status_code == 200
    body = paused.json()
    assert body["charging_mode"] == "PAUSED"
    assert body["override_active"] is False
    assert body["override_until"] is None

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_ev_charger_chargeamp_local_control(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Local Prefs Halo", bridge_enabled=True)
    charger_id = charger["id"]
    assert charger["charging_mode"] == "SMART_CHARGE"

    control = await ac.patch(
        f"/api/sites/akarp/ev-chargers/{charger_id}/control",
        json={
            "charging_mode": "SOLAR_CHARGE",
            "departure_time": "06:30",
            "target_soc_pct": 90,
        },
    )
    assert control.status_code == 200
    body = control.json()
    assert body["charging_mode"] == "SOLAR_CHARGE"
    assert body["departure_time"] == "06:30"
    assert body["target_soc_pct"] == 90

    price_mode = await ac.patch(
        f"/api/sites/akarp/ev-chargers/{charger_id}/control",
        json={"charging_mode": "PRICE_CHARGE"},
    )
    assert price_mode.status_code == 200
    assert price_mode.json()["charging_mode"] == "PRICE_CHARGE"
    assert "PRICE_CHARGE" in price_mode.json()["available_modes"]

    invalid = await ac.patch(
        f"/api/sites/akarp/ev-chargers/{charger_id}/control",
        json={"charging_mode": "INVALID"},
    )
    assert invalid.status_code == 422

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_ev_charger_savings_endpoint(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Savings Halo", bridge_enabled=True)
    charger_id = charger["id"]

    savings = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/savings?days=7")
    assert savings.status_code == 200
    body = savings.json()
    assert body["charger_id"] == charger_id
    assert body["has_data"] is False
    assert body["savings_sek"] == 0.0

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_ev_sessions_and_stats_endpoints(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Accounting Halo", bridge_enabled=True)
    charger_id = charger["id"]

    sessions = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/sessions")
    assert sessions.status_code == 200
    assert sessions.json() == []

    current = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/sessions/current")
    assert current.status_code == 200
    assert current.json() is None

    missing_session = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/sessions/99999")
    assert missing_session.status_code == 404

    stats = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/stats?period=month")
    assert stats.status_code == 200
    body = stats.json()
    assert body["session_count"] == 0
    assert body["total_energy_kwh"] == 0.0
    assert body["savings_baseline"] == "IMMEDIATE_GRID_CHARGING"

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_energy_reasoning_endpoint(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Reasoning Halo", bridge_enabled=True)
    charger_id = charger["id"]

    response = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/energy-reasoning")
    assert response.status_code == 200
    body = response.json()
    assert body["charger_id"] == charger_id
    assert body["bridge_enabled"] is True
    assert isinstance(body["reasoning_steps"], list)

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_energy_balance_endpoints_empty(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="Balance Test")
    charger_id = charger["id"]

    balance = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/energy-balance")
    assert balance.status_code == 200
    body = balance.json()
    assert body["charger_id"] == charger_id
    assert body["status"] == "UNAVAILABLE"

    history = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/energy-balance/history")
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["items"] == []
    assert history_body["total"] == 0

    evse = await ac.get(f"/api/sites/akarp/ev-chargers/{charger_id}/virtual-evse/status")
    assert evse.status_code == 200
    assert evse.json()["virtual_evse_enabled"] is False

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")


@pytest.mark.asyncio
async def test_virtual_evse_enable_and_semp_discovery(client):
    ac, _, _ = client
    charger = await create_charger(ac, "akarp", name="SEMP Test")
    charger_id = charger["id"]

    updated = await ac.put(
        f"/api/sites/akarp/ev-chargers/{charger_id}",
        json={"virtual_evse_enabled": True},
    )
    assert updated.status_code == 200
    assert updated.json()["virtual_evse_enabled"] is True
    assert updated.json()["semp_device_id"] == f"emic-evse-{charger_id}"

    devices = await ac.get("/semp")
    assert devices.status_code == 200
    assert f"emic-evse-{charger_id}" in devices.json()["devices"]

    await ac.delete(f"/api/sites/akarp/ev-chargers/{charger_id}")
