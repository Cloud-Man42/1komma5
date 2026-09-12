"""EMIC user authentication and authorization tests."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_login_success_and_me(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    me = await ac.get("/api/auth/me", cookies=cookies)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@example.com"
    assert "SUPER_ADMIN" in body["roles"]
    assert "password" not in body
    assert "passwordHash" not in body


@pytest.mark.asyncio
async def test_login_invalid_password(auth_client) -> None:
    ac, _ = auth_client
    response = await ac.post("/api/auth/login", json={"username_or_email": "admin@example.com", "password": "wrong"})
    assert response.status_code == 401
    assert "Felaktigt" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_unknown_user(auth_client) -> None:
    ac, _ = auth_client
    response = await ac.post("/api/auth/login", json={"username_or_email": "nobody@example.com", "password": "x"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_disabled_user(auth_client) -> None:
    ac, _ = auth_client
    response = await ac.post("/api/auth/login", json={"username_or_email": "disabled@example.com", "password": "DisabledPass123!"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    csrf = cookies.get("emic_csrf")
    logout = await ac.post("/api/auth/logout", cookies=cookies, headers={"X-CSRF-Token": csrf or ""})
    assert logout.status_code == 200
    me = await ac.get("/api/auth/me", cookies=cookies)
    assert me.status_code == 401


@pytest.mark.asyncio
async def test_break_glass_token_works(auth_client) -> None:
    ac, _ = auth_client
    response = await ac.get("/api/sites", headers={"Authorization": "Bearer break-glass-secret"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_anonymous_rejected_when_auth_enabled(auth_client) -> None:
    ac, _ = auth_client
    response = await ac.get("/api/sites")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_access_user_admin(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/admin/users", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_list_users(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/admin/users", cookies=cookies)
    assert response.status_code == 200
    assert len(response.json()["users"]) >= 3


@pytest.mark.asyncio
async def test_super_admin_can_list_site_options(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    response = await ac.get("/api/admin/users/site-options", cookies=cookies)
    assert response.status_code == 200
    sites = response.json()["sites"]
    assert len(sites) >= 1
    assert {"id", "slug", "name"}.issubset(sites[0].keys())


@pytest.mark.asyncio
async def test_viewer_cannot_list_site_options(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/admin/users/site-options", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_site_isolation_viewer_only_akarp(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    sites = await ac.get("/api/sites", cookies=cookies)
    assert sites.status_code == 200
    slugs = {s["slug"] for s in sites.json()}
    assert "akarp" in slugs
    assert "summer-house-denmark" not in slugs


@pytest.mark.asyncio
async def test_change_password(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "operator@example.com", "OperatorPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/auth/change-password",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"current_password": "OperatorPass123!", "new_password": "NewOperatorPass123!"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_viewer_denied_other_site_dashboard(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/sites/summer-house-denmark/dashboard", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_operator_can_read_akarp_dashboard(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "operator@example.com", "OperatorPass123!")
    response = await ac.get("/api/sites/akarp/dashboard", cookies=cookies)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_viewer_cannot_manage_users(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/admin/users",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={
            "username": "hacker",
            "email": "hacker@example.com",
            "password": "HackerPass123!",
            "displayName": "Hacker",
            "roleIds": [],
            "siteIds": [],
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_password_hash_never_in_api_response(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    users = await ac.get("/api/admin/users", cookies=cookies)
    text = users.text.lower()
    assert "password_hash" not in text
    assert "adminpass" not in text
