"""Unified Module Store API tests (Sprint D)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.db.models import Base
from energy_core.db.models.marketplace_trust_cache import MarketplaceTrustCacheModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier
from energy_core.platform.modules.packages.types import PackageState, SignatureStatus
from energy_core.platform.modules.packages.types import InstalledPackageRecord
from energy_core.seed import seed_sites

FIXTURES = Path(__file__).resolve().parents[2] / "packages" / "energy-core" / "tests" / "fixtures"
CATALOG = FIXTURES / "modules" / "catalog"
STORE_CATALOG = json.loads((FIXTURES / "marketplace" / "store_catalog.json").read_text(encoding="utf-8"))
ADMIN = {"Authorization": "Bearer admin-secret"}


@pytest.fixture
async def store_client(tmp_path):
    db_path = tmp_path / "store.db"
    modules_path = tmp_path / "modules"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_sites(session)
        session.add(
            MarketplaceTrustCacheModel(
                cache_key="default",
                enabled=True,
                cache_state="healthy",
                revocation_state="fresh",
                cache_generation=1,
                snapshot_version=100,
                catalog_json=json.dumps(STORE_CATALOG, sort_keys=True),
                revocations_json=json.dumps({"bundle": {"generation": 1}, "revocations": []}),
                revocation_generation=1,
            )
        )
        publishers = [
            ("emic-official", "EMIC Official", PublisherTier.OFFICIAL),
            ("vendor-verified", "Verified Vendor", PublisherTier.VERIFIED),
            ("community-publisher", "Community Dev", PublisherTier.COMMUNITY),
            ("revoked-publisher", "Revoked Corp", PublisherTier.REVOKED),
        ]
        for pid, name, tier in publishers:
            status = PublisherStatus.REVOKED if tier == PublisherTier.REVOKED else PublisherStatus.ACTIVE
            session.add(
                ModulePublisherModel(
                    publisher_id=pid,
                    display_name=name,
                    tier=tier.value,
                    status=status.value,
                )
            )
        await session.commit()
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        EMIC_MODULES_PATH=str(modules_path),
        EMIC_MODULE_CATALOG_PATH=str(CATALOG),
        EMIC_ADMIN_TOKEN="admin-secret",
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        MARKETPLACE_METADATA_ENABLED=True,
        THIRD_PARTY_RUNTIME_ENABLED=False,
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_store_catalog_requires_admin(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_store_catalog_lists_builtin_and_marketplace(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"page_size": 100})
    assert res.status_code == 200
    body = res.json()
    ids = {m["module_id"] for m in body["modules"]}
    assert "integration.heartbeat" in ids
    assert "integration.official-readonly" in ids
    assert body["total"] >= 5
    assert any(c["count"] > 0 for c in body["categories"])


@pytest.mark.asyncio
async def test_store_search_filters(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"search": "Charge Amps"})
    assert res.status_code == 200
    body = res.json()
    assert any("chargeamps" in m["module_id"] for m in body["modules"])


@pytest.mark.asyncio
async def test_store_category_filter(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"category": "EV Charging"})
    assert res.status_code == 200
    assert all(m["category"] == "EV Charging" or "EV Charging" in m["categories"] for m in res.json()["modules"])


@pytest.mark.asyncio
async def test_store_pagination(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    body = res.json()
    assert len(body["modules"]) <= 2
    assert body["page"] == 1
    assert body["page_size"] == 2


@pytest.mark.asyncio
async def test_store_invalid_sort_defaults(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"sort": "DROP TABLE"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_store_module_detail(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.chargeamps", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["trust_tier"] == "OFFICIAL"
    assert body["summary"]["origin"] == "BUILT_IN"
    assert len(body["capabilities"]) > 0
    assert body["summary"]["control_capable"] is True


@pytest.mark.asyncio
async def test_store_community_denied_in_production(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.community-denied", headers=ADMIN)
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["primary_action"] in {"BLOCKED_BY_POLICY", "REVOKED"}
    assert summary["policy"]["decision"] == "DENY"


@pytest.mark.asyncio
async def test_store_revoked_publisher(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.revoked-module", headers=ADMIN)
    assert res.status_code == 200
    assert res.json()["summary"]["primary_action"] == "REVOKED"


@pytest.mark.asyncio
async def test_store_control_module_runtime_blocked(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.official-control", headers=ADMIN)
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["control_capable"] is True


@pytest.mark.asyncio
async def test_store_xss_sanitized(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.xss-test", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert "<script>" not in body["summary"]["display_name"]
    assert "onerror" not in body["long_description"].lower()


@pytest.mark.asyncio
async def test_store_preflight_non_mutating(store_client) -> None:
    ac, session_factory, _ = store_client
    async with session_factory() as session:
        before = len(await InstalledPackageRepository(session).list_all())
    res = await ac.post(
        "/api/modules/store/integration.official-readonly/1.0.0/preflight",
        headers=ADMIN,
        json={"site_slug": "akarp"},
    )
    assert res.status_code == 200
    body = res.json()
    assert "policy" in body
    assert "permissions" in body
    async with session_factory() as session:
        after = len(await InstalledPackageRepository(session).list_all())
    assert before == after


@pytest.mark.asyncio
async def test_store_invalid_module_id_rejected(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/../etc/passwd", headers=ADMIN)
    assert res.status_code in {400, 404, 422}


@pytest.mark.asyncio
async def test_store_install_blocked_community(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.post(
        "/api/modules/store/integration.community-denied/1.0.0/install",
        headers=ADMIN,
        json={},
    )
    assert res.status_code == 422
    assert res.json()["detail"]["code"] == "INSTALL_BLOCKED"


@pytest.mark.asyncio
async def test_store_security_center(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/security", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert "installed_count" in body
    assert "revoked-publishers" not in body
    assert isinstance(body["revoked_publishers"], list)


@pytest.mark.asyncio
async def test_store_publishers(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/publishers", headers=ADMIN)
    assert res.status_code == 200
    assert len(res.json()) >= 4


@pytest.mark.asyncio
async def test_store_status(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/status", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert body["marketplace_enabled"] is True
    assert "message" in body


@pytest.mark.asyncio
async def test_store_releases(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.official-readonly/releases", headers=ADMIN)
    assert res.status_code == 200
    releases = res.json()
    assert any(r["version"] == "1.0.0" for r in releases)


@pytest.mark.asyncio
async def test_store_catalog_lists_sensibo(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store/integration.sensibo", headers=ADMIN)
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["display_name"] == "Sensibo Climate"
    assert body["summary"]["control_capable"] is False
    caps = {c["capability"] for c in body["capabilities"]}
    assert "hvac.read_temperature" in caps


@pytest.mark.asyncio
async def test_store_preflight_sensibo_readonly(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.post(
        "/api/modules/store/integration.sensibo/1.0.0/preflight",
        headers=ADMIN,
        json={"site_slug": "akarp"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["policy"]["decision"] == "ALLOW"
    assert body["permissions"]


@pytest.mark.asyncio
async def test_store_oversized_search_truncated(store_client) -> None:
    ac, _, _ = store_client
    res = await ac.get("/api/modules/store", headers=ADMIN, params={"search": "x" * 500})
    assert res.status_code == 422
