"""Tenant workspace API tests."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_list_my_tenants(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/tenants/mine", cookies=cookies)
    assert response.status_code == 200
    tenants = response.json()["tenants"]
    assert len(tenants) >= 1
    assert any(t["slug"] == "henrik-home" for t in tenants)


@pytest.mark.asyncio
async def test_select_tenant(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    mine = await ac.get("/api/tenants/mine", cookies=cookies)
    tenant_id = mine.json()["tenants"][0]["id"]
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/tenants/select",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"tenant_id": tenant_id},
    )
    assert response.status_code == 200
    assert response.json()["tenant"]["id"] == tenant_id


@pytest.mark.asyncio
async def test_select_tenant_without_membership_returns_403(auth_client) -> None:
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
