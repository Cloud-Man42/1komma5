"""Load-style concurrent API tests."""

from __future__ import annotations

import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from energy_core.config import Settings


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "load.db"
    settings = Settings(
        _env_file=None,
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        APP_ENV="test",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_concurrent_snapshot_requests(app) -> None:
    transport = ASGITransport(app=app)

    async def one(client: AsyncClient) -> int:
        res = await client.get("/api/sites/akarp/snapshot")
        return res.status_code

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        statuses = await asyncio.gather(*[one(client) for _ in range(10)])
    assert all(status == 200 for status in statuses)
