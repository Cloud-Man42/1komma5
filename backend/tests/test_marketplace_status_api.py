"""Marketplace status/sync API tests."""

from __future__ import annotations

import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from app.deps import set_session_factory
from energy_core.config import Settings
from energy_core.db.models.base import Base
from energy_core.seed import seed_sites

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "energy-core" / "tests" / "fixtures" / "marketplace_tuf"
REPO_DIR = FIXTURE_ROOT / "repository"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture(scope="module")
def tuf_server():
    import os
    import socket

    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    server = ThreadingHTTPServer((host, port), _QuietHandler)

    def serve() -> None:
        os.chdir(REPO_DIR)
        server.serve_forever(poll_interval=0.01)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield f"http://{host}:{port}/metadata/", f"http://{host}:{port}/targets/"
    server.shutdown()


@pytest.fixture
async def marketplace_client(tmp_path, tuf_server):
    metadata_url, targets_url = tuf_server
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_sites(session)
        await session.commit()
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        EMIC_ADMIN_TOKEN="admin-secret",
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_METADATA_URL=metadata_url,
        MARKETPLACE_TARGETS_URL=targets_url,
        MARKETPLACE_TRUSTED_ROOT_PATH=str(FIXTURE_ROOT / "pinned_root.json"),
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_status_requires_admin(marketplace_client):
    response = await marketplace_client.get("/api/modules/marketplace/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_status_uninitialized(marketplace_client):
    response = await marketplace_client.get(
        "/api/modules/marketplace/status",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["metadata_health"] in {"uninitialized", "healthy", "stale", "offline"}


@pytest.mark.asyncio
async def test_status_disabled(tmp_path, tuf_server):
    metadata_url, targets_url = tuf_server
    db_path = tmp_path / "disabled.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        EMIC_ADMIN_TOKEN="admin-secret",
        MARKETPLACE_METADATA_ENABLED=False,
        MARKETPLACE_METADATA_URL=metadata_url,
        MARKETPLACE_TARGETS_URL=targets_url,
        MARKETPLACE_TRUSTED_ROOT_PATH=str(FIXTURE_ROOT / "pinned_root.json"),
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get(
            "/api/modules/marketplace/status",
            headers={"Authorization": "Bearer admin-secret"},
        )
        assert response.status_code == 200
        assert response.json()["metadata_health"] == "disabled"
    await engine.dispose()


@pytest.mark.asyncio
async def test_sync_success(marketplace_client):
    response = await marketplace_client.post(
        "/api/modules/marketplace/sync",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "success"
    status = await marketplace_client.get(
        "/api/modules/marketplace/status",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert status.json()["metadata_health"] == "healthy"
    assert status.json()["cache_generation"] >= 1
