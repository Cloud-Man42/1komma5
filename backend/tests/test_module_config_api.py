"""Module config API tests."""

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
async def admin_config_client(tmp_path):
    db_file = tmp_path / "module-config-admin.db"
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
    headers = {"Authorization": "Bearer admin-secret"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_module_config_get_requires_admin_when_token_configured(tmp_path):
    db_file = tmp_path / "module-config-auth.db"
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
        res = await ac.get("/api/sites/akarp/modules/integration.heartbeat/config")
        assert res.status_code == 401
    await engine.dispose()


@pytest.mark.asyncio
async def test_module_config_get_masks_secrets(admin_config_client):
    ac, _ = admin_config_client
    res = await ac.get("/api/sites/akarp/modules/integration.heartbeat/config")
    assert res.status_code == 200
    body = res.json()
    assert body["module_id"] == "integration.heartbeat"
    assert "password" not in body["config"]
    assert "api_token" not in body["config"]


@pytest.mark.asyncio
async def test_module_config_put_heartbeat_external_id(admin_config_client):
    ac, session_factory = admin_config_client
    res = await ac.put(
        "/api/sites/akarp/modules/integration.heartbeat/config",
        json={"config": {"external_system_id": "test-system-123"}},
    )
    assert res.status_code == 200
    assert res.json()["config"]["external_system_id"] == "test-system-123"
    assert res.json()["restart_required"] == "integration"

    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        assert site.external_system_id == "test-system-123"


@pytest.mark.asyncio
async def test_module_config_put_validation_error(admin_config_client):
    ac, _ = admin_config_client
    res = await ac.put(
        "/api/sites/akarp/modules/integration.mercedes/config",
        json={"config": {}},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_module_config_404_unknown_module(admin_config_client):
    ac, _ = admin_config_client
    res = await ac.get("/api/sites/akarp/modules/does.not.exist/config")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_module_config_put_mercedes_delegates_credentials(admin_config_client):
    ac, session_factory = admin_config_client
    res = await ac.put(
        "/api/sites/akarp/modules/integration.mercedes/config",
        json={"config": {"username": "test-user", "password": "test-secret"}},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["config"]["username"] == "test-user"
    assert "password" not in body["config"]
    async with session_factory() as session:
        from energy_core.db.repositories import SiteRepository
        from energy_core.db.vehicle_repo import VehicleProviderRepository
        from energy_core.secrets import SecretBox

        site = await SiteRepository(session).get_by_slug("akarp")
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        row = await repo.get_or_create(site.id)
        assert row.username == "test-user"
        assert row.encrypted_password
