"""Runtime pilot authorization API tests (Sprint E)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.seed import seed_sites
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ADMIN = {"Authorization": "Bearer admin-secret"}


@pytest.fixture
async def auth_client(tmp_path):
    db_file = tmp_path / "runtime-auth.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
        THIRD_PARTY_RUNTIME_ENABLED=False,
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
        yield client, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_authorization_requires_admin(auth_client):
    client, _ = auth_client
    response = await client.get("/api/modules/runtime/authorizations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_grant_and_list_authorization(auth_client):
    client, _ = auth_client
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    grant = await client.post(
        "/api/modules/runtime/authorizations",
        headers=ADMIN,
        json={
            "module_id": "integration.sensibo",
            "version": "1.0.0",
            "artifact_sha256": "a" * 64,
            "publisher_id": "emic-official",
            "site_id": 1,
            "expires_at": expires,
            "reason": "Sprint E pilot",
        },
    )
    assert grant.status_code == 201
    body = grant.json()
    assert body["module_id"] == "integration.sensibo"
    assert body["active"] is True

    listing = await client.get("/api/modules/runtime/authorizations", headers=ADMIN)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_grant_rejects_wildcard(auth_client):
    client, _ = auth_client
    response = await client.post(
        "/api/modules/runtime/authorizations",
        headers=ADMIN,
        json={
            "module_id": "integration.*",
            "version": "1.0.0",
            "artifact_sha256": "b" * 64,
            "publisher_id": "emic-official",
            "site_id": 1,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_revoke_authorization(auth_client):
    client, _ = auth_client
    grant = await client.post(
        "/api/modules/runtime/authorizations",
        headers=ADMIN,
        json={
            "module_id": "integration.sensibo",
            "version": "1.0.0",
            "artifact_sha256": "c" * 64,
            "publisher_id": "emic-official",
            "site_id": 1,
        },
    )
    auth_id = grant.json()["id"]
    revoked = await client.delete(f"/api/modules/runtime/authorizations/{auth_id}", headers=ADMIN)
    assert revoked.status_code == 200
    assert revoked.json()["active"] is False


@pytest.mark.asyncio
async def test_runtime_list_shows_selective_auth(auth_client):
    client, _ = auth_client
    await client.post(
        "/api/modules/runtime/authorizations",
        headers=ADMIN,
        json={
            "module_id": "integration.sensibo",
            "version": "1.0.0",
            "artifact_sha256": "d" * 64,
            "publisher_id": "emic-official",
            "site_id": 1,
        },
    )
    response = await client.get("/api/modules/runtime", headers=ADMIN)
    assert response.status_code == 200
    body = response.json()
    assert body["selective_authorization_available"] is True
    assert body["active_authorizations"] == 1
