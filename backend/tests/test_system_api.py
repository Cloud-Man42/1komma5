import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def secured_client(tmp_path):
    db_file = tmp_path / "secured-system.db"
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
async def test_heartbeat_config_defaults(client):
    ac, _, _ = client
    res = await ac.get("/api/system/heartbeat-config")
    assert res.status_code == 200
    data = res.json()
    assert data["connection_type"] == "mock"
    assert data["contacting_component"] == "collector"
    assert data["dashboard_refresh_seconds"] == 30
    assert len(data["sites"]) == 2


@pytest.mark.asyncio
async def test_chargeamps_config_endpoint(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "secret-key")

    res = await ac.get("/api/system/chargeamps-config")
    assert res.status_code == 200
    data = res.json()
    assert data["mock"] is False
    assert data["api_key_configured"] is True
    assert data["env_api_key_configured"] is True
    assert data["effective_provider"] == "external"
    assert data["ready"] is True


@pytest.mark.asyncio
async def test_chargeamps_config_endpoint_reports_per_charger_api_key(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_PROVIDER", "web")
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.delenv("CHARGEAMPS_API_KEY", raising=False)
    monkeypatch.setenv("CHARGEAMPS_EMAIL", "user@example.com")
    monkeypatch.setenv("CHARGEAMPS_PASSWORD", "pass")

    create = await ac.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Config Halo",
            "control_source": "chargeamp",
            "bridge_enabled": True,
            "chargeamp_charger_id": "halo-config",
            "chargeamps_api_key": "per-charger-key",
        },
    )
    assert create.status_code == 201

    res = await ac.get("/api/system/chargeamps-config")
    assert res.status_code == 200
    data = res.json()
    assert data["provider"] == "web"
    assert data["effective_provider"] == "external"
    assert data["api_key_configured"] is True
    assert data["env_api_key_configured"] is False
    assert data["charger_api_keys_configured"] >= 1
    assert data["ready"] is True


@pytest.mark.asyncio
async def test_charging_readiness_endpoint(client, monkeypatch):
    ac, _, _ = client
    monkeypatch.setenv("CHARGEAMPS_MOCK", "false")
    monkeypatch.setenv("CHARGEAMPS_API_KEY", "secret-key")

    create = await ac.post(
        "/api/sites/akarp/ev-chargers",
        json={
            "name": "Readiness Halo",
            "control_source": "chargeamp",
            "bridge_enabled": True,
            "chargeamp_charger_id": "halo-1",
        },
    )
    assert create.status_code == 201

    res = await ac.get("/api/system/charging-readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["active_bridge_chargers"] >= 1
    assert data["chargeamps_ready"] is True


@pytest.mark.asyncio
async def test_update_heartbeat_config_local(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "local",
            "host": "192.168.1.100",
            "port": 8080,
            "use_tls": False,
            "api_path": "/api",
            "poll_interval_seconds": 45,
            "username": "",
            "sites": [
                {"slug": "akarp", "external_system_id": "00000000-0000-0000-0000-000000000001"},
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["connection_type"] == "local"
    assert data["host"] == "192.168.1.100"
    assert data["port"] == 8080
    assert data["api_url"] == "http://192.168.1.100:8080/api"
    assert data["poll_interval_seconds"] == 45
    akarp = next(site for site in data["sites"] if site["slug"] == "akarp")
    assert akarp["external_system_id"] == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_update_heartbeat_config_clears_site_system_id_with_null(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "cloud",
            "host": "heartbeat.1komma5grad.com",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "username": "",
            "sites": [
                {"slug": "summer-house-denmark", "external_system_id": None},
            ],
        },
    )
    assert res.status_code == 200
    data = res.json()
    summer = next(site for site in data["sites"] if site["slug"] == "summer-house-denmark")
    assert summer["external_system_id"] is None


@pytest.mark.asyncio
async def test_update_dashboard_refresh_seconds(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "mock",
            "host": "",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "dashboard_refresh_seconds": 5,
            "username": "",
            "sites": [],
        },
    )
    assert res.status_code == 200
    assert res.json()["dashboard_refresh_seconds"] == 5


@pytest.mark.asyncio
async def test_dashboard_refresh_seconds_validation(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "mock",
            "host": "",
            "port": 443,
            "use_tls": True,
            "api_path": "/api",
            "poll_interval_seconds": 60,
            "dashboard_refresh_seconds": 31,
            "username": "",
            "sites": [],
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_heartbeat_config_local_requires_host(client):
    ac, _, _ = client
    res = await ac.put(
        "/api/system/heartbeat-config",
        json={
            "connection_type": "local",
            "host": "",
            "port": 8080,
            "use_tls": False,
            "poll_interval_seconds": 45,
        },
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_timescale_status_requires_admin_token(secured_client):
    ac = secured_client
    res = await ac.get("/api/system/timescale-status")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_timescale_status_skips_on_sqlite(secured_client):
    ac = secured_client
    res = await ac.get(
        "/api/system/timescale-status",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "skipped"
    assert data["reason"] == "not_timescale"
