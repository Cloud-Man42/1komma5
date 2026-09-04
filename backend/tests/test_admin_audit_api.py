"""Tests for admin audit log."""

from __future__ import annotations

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.admin_audit.service import redact_summary
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_client(tmp_path):
    db_file = tmp_path / "admin-audit.db"
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


def test_redact_summary_masks_secrets() -> None:
    summary = redact_summary(
        {
            "username": "admin",
            "password": "secret",
            "api_token": "tok",
            "chargeamps_api_key": "ca-key",
            "nested": {"api_key": "key"},
        }
    )
    assert summary is not None
    assert summary["password"] == "[redacted]"
    assert summary["api_token"] == "[redacted]"
    assert summary["chargeamps_api_key"] == "[redacted]"
    assert summary["nested"]["api_key"] == "[redacted]"
    assert summary["username"] == "admin"


@pytest.mark.asyncio
async def test_admin_audit_log_requires_auth(admin_client) -> None:
    res = await admin_client.get("/api/admin/audit-log")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_audit_log_records_site_update(admin_client) -> None:
    headers = {"Authorization": "Bearer admin-secret"}
    res = await admin_client.put(
        "/api/sites/akarp",
        headers=headers,
        json={"name": "Akarp Audit Test"},
    )
    assert res.status_code == 200
    audit = await admin_client.get("/api/admin/audit-log", headers=headers)
    assert audit.status_code == 200
    entries = audit.json()["entries"]
    assert any(entry["action"] == "site.update" for entry in entries)


@pytest.mark.asyncio
async def test_admin_audit_log_records_apple_device_create(admin_client) -> None:
    headers = {"Authorization": "Bearer admin-secret"}
    res = await admin_client.post(
        "/api/apple-devices",
        headers=headers,
        json={
            "owner_label": "Test",
            "device_name": "Phone",
            "device_type": "iphone",
        },
    )
    assert res.status_code == 201
    audit = await admin_client.get("/api/admin/audit-log", headers=headers)
    assert audit.status_code == 200
    entries = audit.json()["entries"]
    assert any(entry["action"] == "apple_device.create" for entry in entries)
