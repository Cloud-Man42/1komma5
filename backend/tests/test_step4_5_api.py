"""Step 4.5 API hardening tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.deps import set_session_factory
from app.main import create_app
from app.rate_limits import connection_test_rate_limiter
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def step45_client(tmp_path):
    db_file = tmp_path / "step45.db"
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
        yield ac, session_factory, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_apply_module_requires_admin(step45_client):
    ac, _, settings = step45_client
    app = create_app(settings)
    set_session_factory(create_session_factory(create_engine(settings)), settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as unauth:
        res = await unauth.post("/api/sites/akarp/modules/integration.heartbeat/apply")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_apply_module_publishes_restart(step45_client):
    ac, _, _ = step45_client
    enable = await ac.put("/api/sites/akarp/modules/feature.solar-forecast", json={"enabled": True})
    assert enable.status_code == 200
    with patch(
        "energy_core.providers.module_apply.publish_module_restart",
        new=AsyncMock(return_value=True),
    ) as publish:
        res = await ac.post("/api/sites/akarp/modules/feature.solar-forecast/apply")
    assert res.status_code == 200
    body = res.json()
    assert body["module_id"] == "feature.solar-forecast"
    assert body["success"] is True
    publish.assert_awaited()


@pytest.mark.asyncio
async def test_onboard_chargeamps_duplicate_returns_409(step45_client):
    ac, session_factory, _ = step45_client
    async with session_factory() as session:
        from energy_core.db.ev_charger_repo import EvChargerRepository
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        repo = EvChargerRepository(session)
        chargers = await repo.list_for_site(site.id)
        if not chargers:
            await repo.create(
                site.id,
                name="Existing Halo",
                manufacturer="ChargeAmps",
                model="Halo",
                control_source="chargeamp",
                chargeamp_charger_id="dup-halo-id",
                external_charger_id="dup-halo-id",
            )
            await session.commit()
        external_id = "dup-halo-id"

    with patch(
        "energy_core.providers.module_onboard.get_onboard_handler",
    ) as get_handler:
        handler = AsyncMock()
        handler.test_connection = AsyncMock()
        get_handler.return_value = handler
        res = await ac.post(
            "/api/sites/akarp/modules/integration.chargeamps/onboard",
            json={"external_device_id": external_id, "friendly_name": "Duplicate"},
        )
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["code"] == "DEVICE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_connection_test_rate_limited(step45_client):
    ac, _, _ = step45_client
    connection_test_rate_limiter._hits.clear()
    first = await ac.post("/api/sites/akarp/modules/integration.heartbeat/test-connection")
    second = await ac.post("/api/sites/akarp/modules/integration.heartbeat/test-connection")
    assert first.status_code in {200, 422}
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_module_config_includes_configuration_status(step45_client):
    ac, _, _ = step45_client
    res = await ac.get("/api/sites/akarp/modules/integration.heartbeat/config")
    assert res.status_code == 200
    body = res.json()
    assert "configuration_status" in body
    assert "effectively_configured" in body


@pytest.mark.asyncio
async def test_heartbeat_cannot_disable(step45_client):
    ac, _, _ = step45_client
    res = await ac.put("/api/sites/akarp/modules/integration.heartbeat", json={"enabled": False})
    assert res.status_code == 409
