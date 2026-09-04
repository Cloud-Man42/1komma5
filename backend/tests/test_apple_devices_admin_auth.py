"""Admin auth on /api/apple-devices routes."""

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
    db_file = tmp_path / "admin-auth.db"
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
async def test_apple_devices_open_when_admin_token_unset(client) -> None:
    ac, _, _ = client
    response = await ac.get("/api/apple-devices")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_apple_devices_requires_bearer_when_admin_token_set(admin_client: AsyncClient) -> None:
    unauth = await admin_client.get("/api/apple-devices")
    assert unauth.status_code == 401

    authed = await admin_client.get(
        "/api/apple-devices",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200


@pytest.mark.asyncio
async def test_apple_devices_rejects_invalid_admin_token(admin_client: AsyncClient) -> None:
    response = await admin_client.get(
        "/api/apple-devices",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 403
