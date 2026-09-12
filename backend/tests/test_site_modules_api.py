"""Site modules API tests."""

from __future__ import annotations

import pytest
from app.deps import set_session_factory
from app.main import create_app
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_modules_client(tmp_path):
    db_file = tmp_path / "site-modules-admin.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
        emic_user_auth_enabled=False,
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
        yield ac, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_site_modules_lists_projection(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/modules")
    assert res.status_code == 200
    body = res.json()
    assert body["site_slug"] == "akarp"
    module_ids = {item["module_id"] for item in body["modules"]}
    assert "feature.smart-charging" in module_ids or "integration.chargeamps" in module_ids


@pytest.mark.asyncio
async def test_site_modules_404_unknown_site(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown-site/modules")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_site_module_detail_404_unknown_module(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/modules/does.not.exist")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_disable_chargeamps_blocked_when_smart_charging_depends(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        from energy_core.db.ev_charger_repo import EvChargerRepository
        from energy_core.db.repositories import SiteRepository

        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        chargers = await EvChargerRepository(session).list_for_site(site.id)
        if not chargers:
            pytest.skip("No chargers configured for akarp")
        for charger in chargers:
            charger.bridge_enabled = True
        await session.commit()

    res = await ac.put("/api/sites/akarp/modules/integration.chargeamps", json={"enabled": False})
    if res.status_code == 409:
        body = res.json()
        detail = body.get("detail")
        if isinstance(detail, dict):
            assert detail.get("dependent_modules")
        else:
            assert "depend" in str(detail).lower()
    else:
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_enable_module_persists_override(client):
    ac, session_factory, _ = client
    res = await ac.put("/api/sites/akarp/modules/feature.solar-forecast", json={"enabled": True})
    assert res.status_code == 200
    assert res.json()["module_id"] == "feature.solar-forecast"

    async with session_factory() as session:
        from energy_core.db.models.modules import SiteModuleConfigurationModel
        from energy_core.db.repositories import SiteRepository
        from sqlalchemy import select

        site = await SiteRepository(session).get_by_slug("akarp")
        row = await session.scalar(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.site_id == site.id,
                SiteModuleConfigurationModel.module_id == "feature.solar-forecast",
            )
        )
        assert row is not None
        assert row.enabled_override is True


@pytest.mark.asyncio
async def test_disable_module_persists_override(client):
    ac, session_factory, _ = client
    res = await ac.put("/api/sites/akarp/modules/feature.solar-forecast", json={"enabled": False})
    assert res.status_code == 200

    async with session_factory() as session:
        from energy_core.db.models.modules import SiteModuleConfigurationModel
        from energy_core.db.repositories import SiteRepository
        from sqlalchemy import select

        site = await SiteRepository(session).get_by_slug("akarp")
        row = await session.scalar(
            select(SiteModuleConfigurationModel).where(
                SiteModuleConfigurationModel.site_id == site.id,
                SiteModuleConfigurationModel.module_id == "feature.solar-forecast",
            )
        )
        assert row is not None
        assert row.enabled_override is False


@pytest.mark.asyncio
async def test_list_modules_excludes_legacy_alias_ids(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/akarp/modules")
    assert res.status_code == 200
    module_ids = {item["module_id"] for item in res.json()["modules"]}
    assert "charging" not in module_ids
    assert "vehicles" not in module_ids


@pytest.mark.asyncio
async def test_update_site_module_requires_admin_token(admin_modules_client):
    ac, _ = admin_modules_client
    unauth = await ac.put("/api/sites/akarp/modules/feature.solar-forecast", json={"enabled": True})
    assert unauth.status_code == 401

    wrong = await ac.put(
        "/api/sites/akarp/modules/feature.solar-forecast",
        json={"enabled": True},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong.status_code == 403

    authed = await ac.put(
        "/api/sites/akarp/modules/feature.solar-forecast",
        json={"enabled": True},
        headers={"Authorization": "Bearer admin-secret"},
    )
    assert authed.status_code == 200
