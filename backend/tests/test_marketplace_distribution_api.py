"""Marketplace distribution API tests."""

from __future__ import annotations

import json
import socket
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier
from energy_core.seed import seed_sites

pytestmark = pytest.mark.integration

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "packages" / "energy-core" / "tests" / "fixtures" / "marketplace_tuf"
ARTIFACTS_DIR = FIXTURE_ROOT / "repository" / "artifacts"
ARTIFACT_MANIFEST = json.loads((FIXTURE_ROOT / "artifact_manifest.json").read_text(encoding="utf-8"))


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture(scope="module")
def artifact_server():
    import os

    host = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    port = sock.getsockname()[1]
    sock.close()
    server = ThreadingHTTPServer((host, port), _QuietHandler)

    def serve() -> None:
        os.chdir(ARTIFACTS_DIR)
        server.serve_forever(poll_interval=0.01)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    yield f"http://{host}:{port}"
    server.shutdown()


@pytest.fixture
async def distribution_client(tmp_path, artifact_server):
    db_path = tmp_path / "test.db"
    staging = tmp_path / "staging"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_sites(session)
        catalog = {
            "snapshot": {"version": 2},
            "modules": {
                "integration.demo": {
                    "publisher_id": "emic-tests",
                    "releases": {
                        "1.0.0": {
                            "release_id": "integration.demo@1.0.0",
                            "publisher_id": "emic-tests",
                            "artifact_url": f"{artifact_server}/{ARTIFACT_MANIFEST['artifact_name']}",
                            "content_sha256": ARTIFACT_MANIFEST["content_sha256"],
                            "artifact_size": ARTIFACT_MANIFEST["artifact_size"],
                        }
                    },
                }
            },
        }
        session.add(
            MarketplaceTrustCacheModel(
                cache_key="default",
                enabled=True,
                cache_state="healthy",
                revocation_state="fresh",
                cache_generation=1,
                root_version=2,
                timestamp_version=2,
                snapshot_version=2,
                targets_version=2,
                catalog_json=json.dumps(catalog, sort_keys=True),
                revocations_json=json.dumps({"bundle": {"generation": 1}, "revocations": []}),
                revocation_generation=1,
            )
        )
        session.add(
            ModulePublisherModel(
                publisher_id="emic-tests",
                display_name="EMIC Tests",
                tier=PublisherTier.ORG_APPROVED.value,
                status=PublisherStatus.ACTIVE.value,
            )
        )
        await session.commit()
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        EMIC_ADMIN_TOKEN="admin-secret",
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        MARKETPLACE_METADATA_ENABLED=True,
        MARKETPLACE_STAGING_PATH=str(staging),
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_catalog_requires_admin(distribution_client):
    res = await distribution_client.get("/api/modules/marketplace/catalog")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_catalog_lists_releases(distribution_client):
    res = await distribution_client.get(
        "/api/modules/marketplace/catalog",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert res.status_code == 200
    body = res.json()
    assert any(r["module_id"] == "integration.demo" for r in body["releases"])


@pytest.mark.asyncio
async def test_fetch_stages_release(distribution_client):
    res = await distribution_client.post(
        "/api/modules/marketplace/releases/integration.demo/1.0.0/fetch",
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["state"] in {"STAGED", "QUARANTINED"}
    assert body["artifact_id"] > 0
