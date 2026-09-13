"""Mobile PWA summary API tests."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_mobile_summary_includes_warnings_and_actions(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/mobile/summary",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": ["akarp"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "aggregate" in body
    assert "freshnessLabel" in body
    assert isinstance(body["warnings"], list)
    assert isinstance(body["quickActions"], list)


@pytest.mark.asyncio
async def test_mobile_summary_denied_site(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/mobile/summary",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": ["akarp", "summer-house-denmark"]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mobile_summary_rejects_empty_site_list(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/mobile/summary",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_mobile_summary_multi_site_has_currencies(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/mobile/summary",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": ["akarp", "summer-house-denmark"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "currencies" in body
    assert isinstance(body["currencies"], list)
