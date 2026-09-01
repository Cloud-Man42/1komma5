"""Vehicle API route tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle


@pytest.mark.asyncio
async def test_vehicle_config_status_and_list(client, monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    ac, _, _ = client

    config = await ac.get("/api/sites/akarp/vehicles/integration/config")
    assert config.status_code == 200
    body = config.json()
    assert body["enabled"] is False
    assert body["password_configured"] is False

    updated = await ac.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "username": "user@example.com", "password": "secret"},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["password_configured"] is True
    assert "secret" not in updated.text

    status = await ac.get("/api/sites/akarp/vehicles/integration/status")
    assert status.status_code == 200
    assert status.json()["enabled"] is True
    assert "secret" not in status.text

    vehicles = await ac.get("/api/sites/akarp/vehicles")
    assert vehicles.status_code == 200
    assert vehicles.json()["vehicles"] == []

    missing = await ac.get("/api/sites/missing/vehicles")
    assert missing.status_code == 404

    bundle = MercedesTokenBundle(
        access_token="access",
        refresh_token="refresh",
        expires_at=9_999_999_999,
        device_guid="device-guid",
    )
    with patch("app.api.vehicles.MercedesProvider.login", new=AsyncMock(return_value=bundle)):
        login = await ac.post("/api/sites/akarp/vehicles/integration/login")
    assert login.status_code == 200
    assert login.json()["success"] is True

    readiness = await ac.get("/api/system/integrations/vehicle-readiness")
    assert readiness.status_code == 200
    assert readiness.json()["enabled_sites"] >= 1

    missing_correlation = await ac.get("/api/sites/akarp/vehicles/999/halo-correlation")
    assert missing_correlation.status_code == 404

    missing_sessions = await ac.get("/api/sites/akarp/vehicles/999/charge-sessions")
    assert missing_sessions.status_code == 404

    missing_current = await ac.get("/api/sites/akarp/vehicles/999/charge-sessions/current")
    assert missing_current.status_code == 404

    disabled = await ac.post(
        "/api/sites/akarp/vehicles/999/commands/set-target-soc",
        json={"target_soc_percent": 80},
    )
    assert disabled.status_code == 403


@pytest.mark.asyncio
async def test_vehicle_login_reports_stale_encryption(client, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    ac, _, _ = client

    await ac.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "username": "user@example.com", "password": "secret"},
    )

    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    login = await ac.post("/api/sites/akarp/vehicles/integration/login")
    assert login.status_code == 422
    assert "Re-save your password" in login.json()["detail"]


@pytest.mark.asyncio
async def test_vehicle_commands_require_enabled_flag(client, monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    ac, _, _ = client

    await ac.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "username": "user@example.com", "password": "secret"},
    )

    missing_vehicle = await ac.post(
        "/api/sites/akarp/vehicles/999/commands/start-charging",
    )
    assert missing_vehicle.status_code == 403

    with patch("energy_core.vehicles.commands.service.MercedesProvider") as provider_cls:
        provider = AsyncMock()
        provider_cls.return_value = provider
        # Enable commands but vehicle still missing -> 404 after enable check passes
        await ac.put(
            "/api/sites/akarp/vehicles/integration/config",
            json={"commands_enabled": True},
        )
        missing = await ac.post("/api/sites/akarp/vehicles/999/commands/start-charging")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_vehicle_sync_endpoint_returns_fresh_list(client, monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    ac, _, _ = client

    await ac.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "username": "user@example.com", "password": "secret"},
    )

    with patch("app.api.vehicles.VehicleSyncService.sync_site", new=AsyncMock(return_value=())):
        response = await ac.post("/api/sites/akarp/vehicles/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["site_slug"] == "akarp"
    assert "synced_at" in body
    assert body["vehicles_updated"] == 0


@pytest.mark.asyncio
async def test_disable_vehicle_hides_it_from_list(client, monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    ac, session_factory, _ = client

    async with session_factory() as session:
        from energy_core.db.models import SiteModel, VehicleModel
        from sqlalchemy import select

        site = await session.scalar(select(SiteModel).where(SiteModel.slug == "akarp"))
        session.add(
            VehicleModel(
                site_id=site.id,
                provider="mercedes",
                external_id="eqe-vin",
                vin="W1K12345678901234",
                manufacturer="Mercedes-Benz",
                model="EQE",
                display_name="EQE",
                enabled=True,
            )
        )
        glc = VehicleModel(
            site_id=site.id,
            provider="mercedes",
            external_id="glc-vin",
            vin="WDC12345678902594",
            manufacturer="Mercedes-Benz",
            model="GLC",
            display_name="GLC",
            enabled=True,
            charger_id=4,
        )
        session.add(glc)
        await session.commit()
        glc_id = glc.id

    listed = await ac.get("/api/sites/akarp/vehicles")
    assert listed.status_code == 200
    assert len(listed.json()["vehicles"]) == 2

    disabled = await ac.patch(f"/api/sites/akarp/vehicles/{glc_id}", json={"enabled": False})
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    listed = await ac.get("/api/sites/akarp/vehicles")
    assert listed.status_code == 200
    assert len(listed.json()["vehicles"]) == 1
    assert listed.json()["vehicles"][0]["display_name"] == "EQE"


@pytest.mark.asyncio
async def test_raw_attributes_endpoint_empty(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/vehicles/integration/raw-attributes")
    assert response.status_code == 200
    body = response.json()
    assert body["site_slug"] == "akarp"
    assert body["observations"] == []
    assert "token" not in response.text.lower()

    missing = await ac.get("/api/sites/missing/vehicles/integration/raw-attributes")
    assert missing.status_code == 404

    missing_vehicle = await ac.get("/api/sites/akarp/vehicles/integration/raw-attributes?vehicle_id=9999")
    assert missing_vehicle.status_code == 404


@pytest.mark.asyncio
async def test_integration_diagnostics_and_reset(client):
    ac, _, _ = client
    diagnostics = await ac.get("/api/sites/akarp/vehicles/integration/diagnostics")
    assert diagnostics.status_code == 200
    body = diagnostics.json()
    assert body["site_slug"] == "akarp"
    assert "health_status" in body
    assert "integration_events" in body

    reset = await ac.post("/api/sites/akarp/vehicles/integration/actions/reset")
    assert reset.status_code == 200
    assert reset.json()["success"] is True

    unknown = await ac.post("/api/sites/akarp/vehicles/integration/actions/unknown-action")
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_vehicle_charging_stats_endpoint(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/vehicles/1/charging-stats?period=month")
    assert response.status_code in {200, 404}
    if response.status_code == 200:
        body = response.json()
        assert body["period"] == "month"
        assert "total_energy_kwh" in body

    invalid = await ac.get("/api/sites/akarp/vehicles/1/charging-stats?period=invalid")
    assert invalid.status_code == 422
