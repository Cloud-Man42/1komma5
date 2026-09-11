"""External module site configuration API tests (Sprint E)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.seed import seed_sites

ADMIN = {"Authorization": "Bearer admin-secret"}


@pytest.fixture
async def external_client(tmp_path):
    db_file = tmp_path / "external-modules.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_external_config_requires_admin(external_client):
    response = await external_client.get("/api/sites/akarp/modules/integration.sensibo/external-config")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_external_config_upsert_and_get(external_client):
    put = await external_client.put(
        "/api/sites/akarp/modules/integration.sensibo/external-config",
        headers=ADMIN,
        json={
            "api_key": "test-api-key-12345678",
            "poll_interval_seconds": 120,
            "selected_device_ids": ["pod1"],
        },
    )
    assert put.status_code == 200
    body = put.json()
    assert body["credential_configured"] is True
    assert body["selected_device_ids"] == ["pod1"]
    assert body["poll_interval_seconds"] == 120

    get = await external_client.get(
        "/api/sites/akarp/modules/integration.sensibo/external-config",
        headers=ADMIN,
    )
    assert get.status_code == 200
    fetched = get.json()
    assert fetched["credential_configured"] is True
    assert fetched["selected_device_ids"] == ["pod1"]


@pytest.mark.asyncio
async def test_external_config_unknown_site(external_client):
    response = await external_client.put(
        "/api/sites/missing/modules/integration.sensibo/external-config",
        headers=ADMIN,
        json={"api_key": "test-api-key-12345678"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_external_config_short_api_key_rejected(external_client):
    response = await external_client.put(
        "/api/sites/akarp/modules/integration.sensibo/external-config",
        headers=ADMIN,
        json={"api_key": "short"},
    )
    assert response.status_code == 422
