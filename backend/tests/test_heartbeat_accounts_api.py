"""Heartbeat multi-account admin API tests."""

from __future__ import annotations

import base64
import json
import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.auth_probe import AuthProbeResult
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


def _fake_jwt() -> str:
    exp = int(time.time()) + 3600
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


def _gridx_probe() -> AuthProbeResult:
    return AuthProbeResult(
        provider=HeartbeatBackendProvider.GRIDX.value,
        connection_type=HeartbeatConnectionType.CLOUD.value,
        host="api.gridx.de",
        port=443,
        use_tls=True,
        api_path="",
        auth_domain="gridx.eu.auth0.com",
        auth_realm="1komma5grad-authentication-db",
        auth_client_id="client",
        api_url="https://api.gridx.de",
        access_token=_fake_jwt(),
        refresh_token="refresh",
        token_expires_at=datetime.now(UTC),
        probe_path="/account",
        probe_ok=True,
    )


@pytest.fixture
async def admin_accounts_client(tmp_path):
    db_file = tmp_path / "heartbeat-accounts-admin.db"
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
    headers = {"Authorization": "Bearer admin-secret"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as ac:
        yield ac, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_heartbeat_accounts_empty(client):
    ac, _, _ = client
    response = await ac.get("/api/system/heartbeat-accounts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_heartbeat_account(admin_accounts_client):
    ac, _ = admin_accounts_client
    with patch(
        "app.api.heartbeat_accounts.probe_heartbeat_credentials",
        new=AsyncMock(return_value=_gridx_probe()),
    ):
        response = await ac.post(
            "/api/system/heartbeat-accounts",
            json={
                "slug": "denmark",
                "name": "Danmark",
                "username": "dk@example.com",
                "password": "secret",
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "denmark"
    assert body["password_configured"] is True
    assert body["username_masked"] == "d***@example.com"
    assert body["provider"] == "gridx"
    assert body["api_url"] == "https://api.gridx.de"
    assert "username" not in body


@pytest.mark.asyncio
async def test_create_account_rejects_failed_login(admin_accounts_client):
    ac, _ = admin_accounts_client
    with patch(
        "app.api.heartbeat_accounts.probe_heartbeat_credentials",
        new=AsyncMock(side_effect=HeartbeatAuthError("Fel e-post eller lösenord")),
    ):
        response = await ac.post(
            "/api/system/heartbeat-accounts",
            json={
                "slug": "denmark-fail",
                "name": "Danmark",
                "username": "dk@example.com",
                "password": "wrong",
            },
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_duplicate_slug_returns_409(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        await repo.create(
            slug="default",
            name="Default",
            connection_type=HeartbeatConnectionType.CLOUD.value,
        )
        await session.commit()

    with patch(
        "app.api.heartbeat_accounts.probe_heartbeat_credentials",
        new=AsyncMock(return_value=_gridx_probe()),
    ):
        response = await ac.post(
            "/api/system/heartbeat-accounts",
            json={
                "slug": "default",
                "name": "Other",
                "username": "u@example.com",
                "password": "secret",
            },
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_diagnostics_404(admin_accounts_client):
    ac, _ = admin_accounts_client
    response = await ac.get("/api/system/heartbeat-accounts/9999/diagnostics")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_connection(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            provider=HeartbeatBackendProvider.GRIDX.value,
            username="dk@example.com",
            password="secret",
        )
        await session.commit()
        account_id = record.id

    from energy_core.integrations.heartbeat.discovery_service import HeartbeatDiscoveryReport

    report = HeartbeatDiscoveryReport(
        account_id=account_id,
        provider="gridx",
        api_url="https://api.gridx.de",
        authentication_ok=True,
        installations=(),
        raw_paths_probed=("/account",),
    )
    with patch(
        "app.api.heartbeat_accounts.probe_heartbeat_credentials",
        new=AsyncMock(return_value=_gridx_probe()),
    ), patch(
        "app.api.heartbeat_accounts.discover_account_installations",
        new=AsyncMock(return_value=report),
    ):
        response = await ac.post(f"/api/system/heartbeat-accounts/{account_id}/test-connection")
    assert response.status_code == 200
    body = response.json()
    assert body["connected"] is True


@pytest.mark.asyncio
async def test_link_site_to_account(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            connection_type=HeartbeatConnectionType.CLOUD.value,
            username="dk@example.com",
            password="secret",
        )
        await session.commit()
        account_id = record.id

    response = await ac.post(
        f"/api/system/heartbeat-accounts/{account_id}/link-site",
        json={
            "site_slug": "summer-house-denmark",
            "heartbeat_serial_number": "K183-600-000-021-000-P-X",
            "heartbeat_system_id": "11111111-2222-3333-4444-555555555555",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["site_slug"] == "summer-house-denmark"
    assert body["heartbeat_account_id"] == account_id
    assert body["heartbeat_system_id"] == "11111111-2222-3333-4444-555555555555"


@pytest.mark.asyncio
async def test_link_site_stores_gateway_id(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            provider=HeartbeatBackendProvider.GRIDX.value,
        )
        await session.commit()
        account_id = record.id

    gateway_id = "40a3b35b-5b7d-4de1-b045-e4f1728cfe74"
    response = await ac.post(
        f"/api/system/heartbeat-accounts/{account_id}/link-site",
        json={
            "site_slug": "summer-house-denmark",
            "heartbeat_gateway_id": gateway_id,
        },
    )
    assert response.status_code == 200
    assert response.json()["heartbeat_gateway_id"] == gateway_id


@pytest.mark.asyncio
async def test_gridx_diagnostics_runs_probes(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            provider=HeartbeatBackendProvider.GRIDX.value,
            username="dk@example.com",
            password="secret",
        )
        from energy_core.db.models import SiteModel
        from sqlalchemy import select

        site = await session.scalar(select(SiteModel).where(SiteModel.slug == "summer-house-denmark"))
        site.heartbeat_account_id = record.id
        site.heartbeat_system_id = "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"
        site.heartbeat_gateway_id = "40a3b35b-5b7d-4de1-b045-e4f1728cfe74"
        await session.commit()
        account_id = record.id

    from energy_core.integrations.heartbeat.gridx_client import GridXClient, GridXCredentials
    from energy_core.integrations.heartbeat.gridx_diagnostics import GridXDiagnosticsReport, GridXProbeResult

    report = GridXDiagnosticsReport(
        provider="gridx",
        api_url="https://api.gridx.de",
        system_id="91a0e8fc-6e8d-4131-bc49-245d7f3369d9",
        gateway_id="40a3b35b-5b7d-4de1-b045-e4f1728cfe74",
        token_ok=True,
        probes=[
            GridXProbeResult(path="/account", ok=True, status_code=200),
            GridXProbeResult(path="/systems/91a0e8fc-6e8d-4131-bc49-245d7f3369d9/live", ok=True, status_code=200),
        ],
    )

    with patch(
        "energy_core.db.heartbeat_account_repo.login_gridx_token_set",
        new=AsyncMock(return_value=type("T", (), {"access_token": _fake_jwt(), "refresh_token": "r"})()),
    ), patch(
        "app.api.heartbeat_accounts.run_gridx_diagnostics",
        new=AsyncMock(return_value=report),
    ), patch(
        "app.api.heartbeat_accounts.create_heartbeat_client",
        new=AsyncMock(
            return_value=GridXClient(GridXCredentials(api_url="https://api.gridx.de", api_token=_fake_jwt()))
        ),
    ):
        response = await ac.get(f"/api/system/heartbeat-accounts/{account_id}/diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "gridx"
    assert body["token_ok"] is True
    assert body["system_id"] == "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"
    assert any(p["path"] == "/account" and p["ok"] for p in body["probes"])


@pytest.mark.asyncio
async def test_link_site_auto_discovers_system_id(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            connection_type=HeartbeatConnectionType.CLOUD.value,
            username="dk@example.com",
            password="secret",
        )
        await session.commit()
        account_id = record.id

    from energy_core.integrations.heartbeat.serial_matcher import SerialMatchResult

    discover_mock = AsyncMock(
        return_value=SerialMatchResult(
            serial="K183-600-000-021-000-P-X",
            found=True,
            resolved_system_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        ),
    )
    with patch(
        "app.api.heartbeat_accounts.discover_system_id_for_serial",
        discover_mock,
    ):
        response = await ac.post(
            f"/api/system/heartbeat-accounts/{account_id}/link-site",
            json={
                "site_slug": "summer-house-denmark",
                "heartbeat_serial_number": "K183-600-000-021-000-P-X",
            },
        )
    assert response.status_code == 200, response.text
    discover_mock.assert_awaited_once()
    body = response.json()
    assert body["heartbeat_system_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_discover_endpoint(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            provider=HeartbeatBackendProvider.GRIDX.value,
            username="dk@example.com",
            password="secret",
        )
        await session.commit()
        account_id = record.id

    from energy_core.integrations.heartbeat.discovery_service import HeartbeatDiscoveryReport, HeartbeatInstallation

    report = HeartbeatDiscoveryReport(
        account_id=account_id,
        provider="gridx",
        api_url="https://api.gridx.de",
        authentication_ok=True,
        installations=(
            HeartbeatInstallation(
                name="Denmark",
                system_id="91a0e8fc-6e8d-4131-bc49-245d7f3369d9",
                serial_number="K183-600-000-021-000-P-X",
            ),
        ),
        raw_paths_probed=("/account", "/systems"),
    )
    with patch(
        "energy_core.db.heartbeat_account_repo.login_gridx_token_set",
        new=AsyncMock(return_value=type("T", (), {"access_token": _fake_jwt(), "refresh_token": "r"})()),
    ), patch(
        "app.api.heartbeat_accounts.discover_account_installations",
        new=AsyncMock(return_value=report),
    ):
        response = await ac.post(f"/api/system/heartbeat-accounts/{account_id}/discover")
    assert response.status_code == 200
    body = response.json()
    assert body["installations"][0]["serial_number"] == "K183-600-000-021-000-P-X"


@pytest.mark.asyncio
async def test_global_diagnostics(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        await repo.create(slug="default", name="Default", provider=HeartbeatBackendProvider.ONEKOMMAFIVE.value)
        await session.commit()

    with patch(
        "app.api.heartbeat_accounts.discover_account_installations",
        new=AsyncMock(side_effect=Exception("skip live")),
    ):
        response = await ac.get("/api/system/heartbeat/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert len(body["accounts"]) >= 1
    assert body["comparison"]["separate_account_context"] in {"YES", "UNKNOWN"}


@pytest.mark.asyncio
async def test_link_site_rejects_duplicate_system_id(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            connection_type=HeartbeatConnectionType.CLOUD.value,
        )
        from energy_core.db.models import SiteModel
        from sqlalchemy import select

        akarp = await session.scalar(select(SiteModel).where(SiteModel.slug == "akarp"))
        akarp.heartbeat_system_id = "ec892788-0a43-46a4-bd25-b4bbc22ab6e3"
        await session.commit()
        account_id = record.id

    response = await ac.post(
        f"/api/system/heartbeat-accounts/{account_id}/link-site",
        json={
            "site_slug": "summer-house-denmark",
            "heartbeat_system_id": "ec892788-0a43-46a4-bd25-b4bbc22ab6e3",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_link_site_unknown_site_404(admin_accounts_client):
    ac, session_factory = admin_accounts_client
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            connection_type=HeartbeatConnectionType.CLOUD.value,
        )
        await session.commit()
        account_id = record.id

    response = await ac.post(
        f"/api/system/heartbeat-accounts/{account_id}/link-site",
        json={"site_slug": "no-such-site"},
    )
    assert response.status_code == 404
