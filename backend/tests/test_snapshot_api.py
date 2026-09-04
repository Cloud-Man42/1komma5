"""Snapshot API tests."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from energy_core.config import Settings


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "snapshot.db"
    settings = Settings(
        _env_file=None,
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path.as_posix()}",
        APP_ENV="test",
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_snapshot_404_unknown_site(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/sites/unknown/snapshot")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_snapshot_returns_payload_for_seeded_site(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/sites/akarp/snapshot")
    assert res.status_code == 200
    body = res.json()
    assert body["site"]["slug"] == "akarp"
    assert "freshness" in body
    assert "generated_at" in body


@pytest.mark.asyncio
async def test_performance_metrics_endpoint(app) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/api/sites/akarp/snapshot")
        res = await client.get("/api/system/performance")
    assert res.status_code == 200
    body = res.json()
    assert "request_count" in body
    assert "cache" in body
    assert body["cache"]["backend"] == "memory"
    assert body["cache"]["redis_configured"] is False
    assert body["cache"]["snapshot_pubsub_configured"] is False
    assert "site_snapshots" in body
    assert isinstance(body["site_snapshots"], list)
    assert "tasks" in body
    assert isinstance(body["tasks"], dict)


@pytest.mark.asyncio
async def test_snapshot_sse_generator_emits_initial_payload(client) -> None:
    from unittest.mock import AsyncMock, patch

    from app.api.snapshot import _snapshot_sse_generator
    from energy_core.db.repositories import SiteRepository

    _ac, session_factory, settings = client
    request = AsyncMock()
    request.is_disconnected = AsyncMock(return_value=True)

    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        with patch(
            "app.api.snapshot.snapshot_pubsub_available",
            AsyncMock(return_value=False),
        ):
            chunks = [
                chunk
                async for chunk in _snapshot_sse_generator(request, session, site, settings)
            ]

    assert len(chunks) == 1
    assert chunks[0].startswith("data: ")
    payload = json.loads(chunks[0].removeprefix("data: ").strip())
    assert payload["site"]["slug"] == "akarp"
