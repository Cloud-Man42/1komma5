"""Widget API and Apple device admin tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from helpers import seed_recent_readings

WIDGET_ALLOWLIST = {
    "apiVersion",
    "site",
    "solar",
    "house",
    "battery",
    "grid",
    "ev",
    "economy",
    "smartCharging",
    "emic",
    "systemStatus",
    "updatedAt",
    "dataAgeSeconds",
    "isStale",
}


async def _create_device(ac, *, owner: str = "Henrik", name: str = "Henriks iPhone") -> dict:
    response = await ac.post(
        "/api/apple-devices",
        json={
            "owner_label": owner,
            "device_name": name,
            "device_type": "iphone",
            "default_site_slug": "akarp",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_widget_status_requires_auth(client):
    ac, _, _ = client
    response = await ac.get("/api/v1/widget/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_widget_status_returns_camel_case_payload(client):
    ac, session_factory, settings = client
    device = await _create_device(ac)
    await seed_recent_readings(
        session_factory,
        settings,
        "akarp",
        [(5420, 1610, 0, 1470, 74)],
    )
    response = await ac.get("/api/v1/widget/status/akarp", headers=_auth_headers(device["token"]))
    assert response.status_code == 200
    body = response.json()
    assert body["apiVersion"] == "1.0"
    assert body["site"]["id"] == "akarp"
    assert body["solar"]["powerKw"] == pytest.approx(5.42, abs=0.01)
    assert body["battery"]["state"] == "idle"
    assert body["grid"]["direction"] == "export"
    assert set(body.keys()).issubset(WIDGET_ALLOWLIST | {"apiVersion"})


@pytest.mark.asyncio
async def test_widget_status_unknown_site_returns_404(client):
    ac, _, _ = client
    device = await _create_device(ac)
    response = await ac.get(
        "/api/v1/widget/status/missing",
        headers=_auth_headers(device["token"]),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_widget_revoked_token_returns_401(client):
    ac, _, _ = client
    device = await _create_device(ac)
    revoke = await ac.post(f"/api/apple-devices/{device['id']}/revoke")
    assert revoke.status_code == 200
    response = await ac.get("/api/v1/widget/status", headers=_auth_headers(device["token"]))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_widget_forbidden_without_scope(client):
    ac, session_factory, _ = client
    from energy_core.auth.device_tokens import generate_device_token
    from energy_core.db.apple_device_repo import AppleDeviceRepository

    async with session_factory() as session:
        repo = AppleDeviceRepository(session)
        generated = generate_device_token()
        await repo.create(
            owner_label="Anna",
            device_name="Annas iPhone",
            device_type="iphone",
            generated=generated,
            scopes="energy.read",
        )
        await session.commit()
        token = generated.token

    response = await ac.get("/api/v1/widget/status", headers=_auth_headers(token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_widget_summary_lists_both_sites(client):
    ac, session_factory, settings = client
    device = await _create_device(ac)
    await seed_recent_readings(session_factory, settings, "akarp", [(3000, 1500, 0, 500, 80)])
    await seed_recent_readings(
        session_factory,
        settings,
        "summer-house-denmark",
        [(2100, 820, 0, 420, 91)],
    )
    response = await ac.get("/api/v1/widget/summary", headers=_auth_headers(device["token"]))
    assert response.status_code == 200
    body = response.json()
    assert len(body["sites"]) == 2
    assert body["totals"]["solarPowerKw"] is not None


@pytest.mark.asyncio
async def test_widget_marks_stale_data(client):
    ac, session_factory, settings = client
    device = await _create_device(ac)
    from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
    from energy_core.domain import NormalizedEnergyReading

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        await repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime.now(UTC) - timedelta(minutes=10),
                solar_production_w=1000,
                consumption_w=800,
                grid_import_w=0,
                grid_export_w=200,
                battery_soc_pct=70,
                battery_power_w=100,
            ),
        )
        await session.commit()

    response = await ac.get("/api/v1/widget/status/akarp", headers=_auth_headers(device["token"]))
    assert response.status_code == 200
    body = response.json()
    assert body["isStale"] is True


@pytest.mark.asyncio
async def test_widget_rate_limit_returns_429(client):
    ac, _, settings = client
    from app.widget_auth import WIDGET_RATE_LIMITER

    WIDGET_RATE_LIMITER._windows.clear()
    settings.widget_rate_limit_per_minute = 1
    device = await _create_device(ac)
    headers = _auth_headers(device["token"])
    first = await ac.get("/api/v1/widget/me", headers=headers)
    assert first.status_code == 200
    second = await ac.get("/api/v1/widget/me", headers=headers)
    assert second.status_code == 429
    assert "retry-after" in second.headers


@pytest.mark.asyncio
async def test_widget_payload_has_no_secret_fields(client):
    ac, session_factory, settings = client
    device = await _create_device(ac)
    await seed_recent_readings(session_factory, settings, "akarp", [(1000, 800, 0, 200, 70)])
    response = await ac.get("/api/v1/widget/status/akarp", headers=_auth_headers(device["token"]))
    payload = json.dumps(response.json()).lower()
    for forbidden in ("chargeamps", "heartbeat", "modbus", "api_key", "password", "token_hash"):
        assert forbidden not in payload


@pytest.mark.asyncio
async def test_admin_create_list_and_revoke_device(client):
    ac, _, _ = client
    created = await _create_device(ac, owner="Anna", name="Annas iPhone")
    assert created["token"].startswith("emic_")
    listed = await ac.get("/api/apple-devices")
    assert listed.status_code == 200
    assert any(item["id"] == created["id"] for item in listed.json())
    revoked = await ac.post(f"/api/apple-devices/{created['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_admin_rename_device(client):
    ac, _, _ = client
    created = await _create_device(ac)
    response = await ac.patch(
        f"/api/apple-devices/{created['id']}",
        json={"device_name": "Henriks iPhone 16"},
    )
    assert response.status_code == 200
    assert response.json()["device_name"] == "Henriks iPhone 16"
