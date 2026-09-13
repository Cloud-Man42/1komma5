"""Cross-tenant security regression tests."""

from __future__ import annotations

import pytest
from auth_helpers import auth_login as _login
from energy_core.auth.passwords import hash_password
from energy_core.auth.repos.user_repo import RoleRepository, UserRepository
from energy_core.auth.seed_rbac import ensure_rbac_seed
from energy_core.config import Settings
from energy_core.db.models import Base, SiteModel
from energy_core.db.repositories import SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.seed import seed_sites
from energy_core.tenancy.repo import TenantRepository
from energy_core.tenancy.sync import sync_tenant_memberships_for_default_tenant
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def multi_tenant_client(tmp_path):
    db_file = tmp_path / "multi-tenant.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        emic_admin_token="break-glass-secret",
        emic_user_auth_enabled=True,
        emic_cookie_secure=False,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await ensure_rbac_seed(session)
        tenant_repo = TenantRepository(session)
        default_tenant = await tenant_repo.get_by_slug("henrik-home")
        assert default_tenant is not None

        customer_a = await tenant_repo.create_tenant(
            name="Customer A",
            display_name="Customer A",
            slug="customer-a",
        )
        customer_site = SiteModel(
            slug="customer-a-site",
            name="Customer A Site",
            timezone="Europe/Stockholm",
            tenant_id=customer_a.id,
        )
        session.add(customer_site)
        await session.flush()

        user_repo = UserRepository(session)
        admin_role = await RoleRepository(session).get_by_name("SUPER_ADMIN")
        viewer_role = await RoleRepository(session).get_by_name("VIEWER")
        sites = await SiteRepository(session).list_all()
        henrik_sites = [s for s in sites if s.tenant_id == default_tenant.id]

        admin = await user_repo.create_user(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("AdminPass123!"),
            display_name="Admin",
        )
        await user_repo.set_roles(admin.id, [admin_role.id])
        await user_repo.set_site_access(admin.id, [s.id for s in sites])

        henrik_viewer = await user_repo.create_user(
            username="viewer",
            email="viewer@example.com",
            password_hash=hash_password("ViewerPass123!"),
            display_name="Viewer",
        )
        await user_repo.set_roles(henrik_viewer.id, [viewer_role.id])
        akarp = next(s for s in henrik_sites if s.slug == "akarp")
        await user_repo.set_site_access(henrik_viewer.id, [akarp.id])

        await sync_tenant_memberships_for_default_tenant(session)

        customer_user = await user_repo.create_user(
            username="customer-a",
            email="customer-a@example.com",
            password_hash=hash_password("CustomerPass123!"),
            display_name="Customer A User",
        )
        await user_repo.set_roles(customer_user.id, [viewer_role.id])
        await user_repo.set_site_access(customer_user.id, [customer_site.id])

        customer_membership = await tenant_repo.create_membership(customer_a.id, customer_user.id)
        await tenant_repo.set_membership_roles(customer_membership.id, [viewer_role.id])
        await tenant_repo.set_membership_site_access(customer_membership.id, [customer_site.id])
        await session.commit()

    from app.deps import set_session_factory
    from app.main import create_app

    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, settings, customer_a.id, customer_site.slug
    await engine.dispose()


@pytest.mark.asyncio
async def test_viewer_cannot_access_denmark_site(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/sites/summer-house-denmark/dashboard", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_access_akarp(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/sites/akarp/dashboard", cookies=cookies)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_users_scoped_to_tenant(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/admin/users", cookies=cookies)
    assert response.status_code == 200
    emails = {u["email"] for u in response.json()["users"]}
    assert "admin@example.com" in emails


@pytest.mark.asyncio
async def test_tenant_spoofing_user_create_rejected(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/admin/users",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={
            "username": "tenantb-user",
            "email": "tenantb-user@example.com",
            "password": "ValidPass123!",
            "display_name": "Tenant B",
            "role_ids": [],
            "site_ids": [],
            "tenant_id": 99999,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_henrik_user_cannot_access_customer_a_site(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/dashboard", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_customer_a_user_cannot_access_akarp(multi_tenant_client) -> None:
    ac, _, _customer_a_id, _customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    response = await ac.get("/api/sites/akarp/dashboard", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_customer_a_user_can_access_own_site(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/dashboard", cookies=cookies)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_select_requires_membership(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/tenants/select",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"tenant_id": 99999},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_site_options_requires_users_read(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/admin/users/site-options", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_sites_respects_tenant_membership(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    response = await ac.get("/api/sites", cookies=cookies)
    assert response.status_code == 200
    slugs = {s["slug"] for s in response.json()}
    assert customer_slug in slugs
    assert "akarp" not in slugs


@pytest.mark.asyncio
async def test_spa_route_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/spa/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_vehicle_route_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/vehicles", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_prices_route_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/prices/current", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_energy_control_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/energy-control/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_heartbeat_bridge_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/heartbeat-bridge/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_solar_intelligence_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/solar-intelligence/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_ev_chargers_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/ev-chargers", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_climate_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/climate/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_mobile_summary_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/mobile/sites/{customer_slug}/summary", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_admin_users_not_visible_cross_tenant(multi_tenant_client) -> None:
    ac, _, _customer_a_id, _customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    response = await ac.get("/api/admin/users", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_mine_lists_only_member_tenants(multi_tenant_client) -> None:
    ac, _, customer_a_id, _customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    response = await ac.get("/api/tenants/mine", cookies=cookies)
    assert response.status_code == 200
    tenant_ids = {t["id"] for t in response.json()["tenants"]}
    assert customer_a_id in tenant_ids
    assert len(tenant_ids) == 1


@pytest.mark.asyncio
async def test_select_valid_tenant_succeeds(multi_tenant_client) -> None:
    ac, _, customer_a_id, _customer_slug = multi_tenant_client
    cookies = await _login(ac, "customer-a@example.com", "CustomerPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/tenants/select",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"tenant_id": customer_a_id},
    )
    assert response.status_code == 200
    assert response.json()["tenant"]["id"] == customer_a_id


@pytest.mark.asyncio
async def test_current_tenant_after_auto_select(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/tenants/current", cookies=cookies)
    assert response.status_code == 200
    assert response.json()["tenant"]["slug"] == "henrik-home"


@pytest.mark.asyncio
async def test_price_engine_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/price-engine/status", cookies=cookies)
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_solar_forecast_cross_tenant_blocked(multi_tenant_client) -> None:
    ac, _, _customer_a_id, customer_slug = multi_tenant_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{customer_slug}/solar-forecast/summary", cookies=cookies)
    assert response.status_code in (403, 404)
