"""Platform tenant CRUD API tests."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_list_platform_tenants_as_admin(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/platform/tenants", cookies=cookies)
    assert response.status_code == 200
    tenants = response.json()["tenants"]
    assert any(t["slug"] == "henrik-home" for t in tenants)


@pytest.mark.asyncio
async def test_list_platform_tenants_denied_for_viewer(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/platform/tenants", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_platform_tenant(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={
            "name": "Acme Corp",
            "display_name": "Acme Corp",
            "slug": "acme-corp",
            "timezone": "Europe/Stockholm",
            "default_currency": "SEK",
        },
    )
    assert response.status_code == 201
    body = response.json()["tenant"]
    assert body["slug"] == "acme-corp"
    assert body["isActive"] is True
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_create_platform_tenant_duplicate_slug_returns_409(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    payload = {
        "name": "Dup Tenant",
        "display_name": "Dup Tenant",
        "slug": "dup-tenant",
    }
    first = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json=payload,
    )
    assert first.status_code == 201
    second = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json=payload,
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_platform_tenant_invalid_slug_returns_422(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={
            "name": "Bad Slug",
            "display_name": "Bad Slug",
            "slug": "Bad Slug!",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_platform_tenant_disable(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    created = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={
            "name": "Disable Me",
            "display_name": "Disable Me",
            "slug": "disable-me",
        },
    )
    tenant_id = created.json()["tenant"]["id"]
    response = await ac.patch(
        f"/api/platform/tenants/{tenant_id}",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"is_active": False},
    )
    assert response.status_code == 200
    body = response.json()["tenant"]
    assert body["isActive"] is False
    assert body["status"] == "disabled"


@pytest.mark.asyncio
async def test_get_platform_tenant_not_found(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/platform/tenants/99999", cookies=cookies)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_empty_platform_tenant(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    created = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"name": "Delete Me", "display_name": "Delete Me", "slug": "delete-me"},
    )
    tenant_id = created.json()["tenant"]["id"]
    response = await ac.delete(
        f"/api/platform/tenants/{tenant_id}",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_default_tenant_returns_409(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    tenants = await ac.get("/api/platform/tenants", cookies=cookies)
    default_id = next(t["id"] for t in tenants.json()["tenants"] if t["slug"] == "henrik-home")
    response = await ac.delete(
        f"/api/platform/tenants/{default_id}",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_platform_tenant_membership_lifecycle(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    created = await ac.post(
        "/api/platform/tenants",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"name": "Members Co", "display_name": "Members Co", "slug": "members-co"},
    )
    tenant_id = created.json()["tenant"]["id"]

    add = await ac.post(
        f"/api/platform/tenants/{tenant_id}/members",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"email": "viewer@example.com"},
    )
    assert add.status_code == 201
    assert add.json()["member"]["email"] == "viewer@example.com"

    listed = await ac.get(f"/api/platform/tenants/{tenant_id}/members", cookies=cookies)
    assert listed.status_code == 200
    assert any(m["email"] == "viewer@example.com" for m in listed.json()["members"])

    duplicate = await ac.post(
        f"/api/platform/tenants/{tenant_id}/members",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"email": "viewer@example.com"},
    )
    assert duplicate.status_code == 409

    removed = await ac.delete(
        f"/api/platform/tenants/{tenant_id}/members/{add.json()['member']['userId']}",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert removed.status_code == 204
