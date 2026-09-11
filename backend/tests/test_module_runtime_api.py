"""Runtime isolation API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.seed import seed_sites
from app.deps import set_session_factory
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def runtime_client(tmp_path):
    db_file = tmp_path / "runtime-api.db"
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
async def test_runtime_list_requires_admin(runtime_client):
    client, _ = runtime_client
    response = await client.get("/api/modules/runtime")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_runtime_list_blocked_message(runtime_client):
    client, _ = runtime_client
    response = await client.get("/api/modules/runtime", headers={"Authorization": "Bearer admin-secret"})
    assert response.status_code == 200
    body = response.json()
    assert body["runtime_blocked"] is True
    assert "blocked" in body["message"].lower()
