"""Governance admin API tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models.base import Base
from energy_core.platform.modules.governance.publisher_repository import PublisherRepository
from energy_core.seed import seed_sites

pytestmark = pytest.mark.integration


@pytest.fixture
async def governance_client(tmp_path):
    db_path = tmp_path / "gov.db"
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
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, session_factory, f"sqlite+aiosqlite:///{db_path}"
    await engine.dispose()


@pytest.mark.asyncio
async def test_governance_requires_admin(governance_client):
    client, _, _ = governance_client
    response = await client.get("/api/modules/governance/publishers")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_publisher_and_evaluate(governance_client):
    client, _, _ = governance_client
    headers = {"Authorization": "Bearer admin-secret"}
    create = await client.post(
        "/api/modules/governance/publishers",
        headers=headers,
        json={"publisher_id": "emic", "display_name": "EMIC Official", "tier": "OFFICIAL"},
    )
    assert create.status_code == 201
    await client.post("/api/modules/governance/publishers/emic/verify", headers=headers)

    evaluate = await client.post(
        "/api/modules/governance/evaluate",
        headers=headers,
        json={"module_id": "demo.mod", "publisher_id": "emic", "action": "INSTALL"},
    )
    assert evaluate.status_code == 200
    body = evaluate.json()
    assert body["decision"] == "ALLOW"


@pytest.mark.asyncio
async def test_community_denied_in_production_evaluate(tmp_path):
    db_path = tmp_path / "prod-gov.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await seed_sites(session)
        repo = PublisherRepository(session)
        await repo.create(publisher_id="community-pub", display_name="Community", tier="COMMUNITY")
        await repo.transition_status("community-pub", "ACTIVE")
        await session.commit()

    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_path}",
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer admin-secret"}
        response = await client.post(
            "/api/modules/governance/evaluate",
            headers=headers,
            json={"module_id": "demo.mod", "publisher_id": "community-pub", "action": "INSTALL"},
        )
        assert response.status_code == 200
        assert response.json()["decision"] == "DENY"
        assert "COMMUNITY_NOT_ALLOWED" in response.json()["reason_codes"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_policy_update_conflict(governance_client):
    client, _, _ = governance_client
    headers = {"Authorization": "Bearer admin-secret"}
    current = await client.get("/api/modules/governance/policy", headers=headers)
    version = current.json()["policy_version"]
    ok = await client.put(
        "/api/modules/governance/policy",
        headers=headers,
        json={"expected_version": version, "allowed_tiers": ["OFFICIAL"]},
    )
    assert ok.status_code == 200
    conflict = await client.put(
        "/api/modules/governance/policy",
        headers=headers,
        json={"expected_version": version, "allowed_tiers": ["VERIFIED"]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "POLICY_CONFLICT"


@pytest.mark.asyncio
async def test_policy_history_after_update(governance_client):
    client, _, _ = governance_client
    headers = {"Authorization": "Bearer admin-secret"}
    current = await client.get("/api/modules/governance/policy", headers=headers)
    version = current.json()["policy_version"]
    await client.put(
        "/api/modules/governance/policy",
        headers=headers,
        json={"expected_version": version, "allowed_tiers": ["OFFICIAL", "VERIFIED"]},
    )
    history = await client.get("/api/modules/governance/policy/history", headers=headers)
    assert history.status_code == 200
    body = history.json()
    assert len(body) >= 1
    assert body[0]["policy_version"] == version


@pytest.mark.asyncio
async def test_revoked_publisher_denied(governance_client):
    client, _, _ = governance_client
    headers = {"Authorization": "Bearer admin-secret"}
    await client.post(
        "/api/modules/governance/publishers",
        headers=headers,
        json={"publisher_id": "bad-pub", "display_name": "Bad", "tier": "ORG_APPROVED"},
    )
    await client.post("/api/modules/governance/publishers/bad-pub/verify", headers=headers)
    await client.post("/api/modules/governance/publishers/bad-pub/revoke", headers=headers)
    evaluate = await client.post(
        "/api/modules/governance/evaluate",
        headers=headers,
        json={"module_id": "demo.mod", "publisher_id": "bad-pub", "action": "INSTALL"},
    )
    assert evaluate.status_code == 200
    assert evaluate.json()["decision"] == "DENY"
    assert "PUBLISHER_REVOKED" in evaluate.json()["reason_codes"]
