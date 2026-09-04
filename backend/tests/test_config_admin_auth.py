"""Admin auth on configuration mutation routes."""

from __future__ import annotations

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_client(tmp_path):
    db_file = tmp_path / "config-admin-auth.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_heartbeat_config_put_open_when_admin_token_unset(client) -> None:
    ac, _, _ = client
    response = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "mock",
            "host": "",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "username": "",
            "sites": [],
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_heartbeat_config_put_requires_bearer_when_admin_token_set(admin_client: AsyncClient) -> None:
    unauth = await admin_client.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "mock",
            "host": "",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "username": "",
            "sites": [],
        },
    )
    assert unauth.status_code == 401

    authed = await admin_client.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "mock",
            "host": "",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "username": "",
            "sites": [],
        },
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200


@pytest.mark.asyncio
async def test_spa_config_put_requires_bearer_when_admin_token_set(admin_client: AsyncClient) -> None:
    unauth = await admin_client.put(
        "/api/sites/akarp/spa/config",
        json={"integration_enabled": True},
    )
    assert unauth.status_code == 401

    authed = await admin_client.put(
        "/api/sites/akarp/spa/config",
        json={"integration_enabled": True},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200


@pytest.mark.asyncio
async def test_site_create_requires_bearer_when_admin_token_set(admin_client: AsyncClient) -> None:
    payload = {
        "slug": "test-site",
        "name": "Test Site",
        "timezone": "Europe/Stockholm",
    }
    unauth = await admin_client.post("/api/sites", json=payload)
    assert unauth.status_code == 401

    authed = await admin_client.post(
        "/api/sites",
        json=payload,
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 201


@pytest.mark.asyncio
async def test_ev_charger_create_requires_bearer_when_admin_token_set(admin_client: AsyncClient) -> None:
    unauth = await admin_client.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Test Halo",
            "control_source": "chargeamp",
            "bridge_enabled": True,
            "chargeamp_charger_id": "test-halo",
        },
    )
    assert unauth.status_code == 401

    authed = await admin_client.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Test Halo",
            "control_source": "chargeamp",
            "bridge_enabled": True,
            "chargeamp_charger_id": "test-halo",
        },
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 201


@pytest.mark.asyncio
async def test_vehicle_integration_config_put_requires_bearer_when_admin_token_set(
    admin_client: AsyncClient,
) -> None:
    unauth = await admin_client.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "region": "EMEA", "username": "user@example.com"},
    )
    assert unauth.status_code == 401

    authed = await admin_client.put(
        "/api/sites/akarp/vehicles/integration/config",
        json={"enabled": True, "region": "EMEA", "username": "user@example.com"},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200
