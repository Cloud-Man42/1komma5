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
