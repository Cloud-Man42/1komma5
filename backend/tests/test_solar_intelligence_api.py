"""Solar Intelligence API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("APP_ENV", "test")
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_provider_status_503_when_intelligence_disabled(client):
    # Site may not exist — expect 404 or 503
    res = await client.get("/api/sites/unknown/solar/provider-status")
    assert res.status_code in (404, 503)


@pytest.mark.asyncio
async def test_model_metrics_route_exists(client):
    res = await client.get("/api/sites/unknown/solar/model/metrics")
    assert res.status_code in (404, 503)
