"""Multi-site overview and site selection API tests."""

from __future__ import annotations

import pytest
from energy_core.multi_site.service import multisite_cache_key

from auth_helpers import auth_login as _login


@pytest.mark.asyncio
async def test_multisite_cache_key_sorted():
    assert multisite_cache_key(["b", "a"]) == multisite_cache_key(["a", "b"])


@pytest.mark.asyncio
async def test_viewer_cannot_request_denied_site(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/multi-site/overview",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": ["akarp", "summer-house-denmark"]},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_multi_site_overview(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")
    response = await ac.post(
        "/api/multi-site/overview",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"site_slugs": ["akarp"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "aggregate" in body
    assert "sites" in body
    assert len(body["sites"]) == 1


@pytest.mark.asyncio
async def test_site_selection_get_and_patch(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "admin@example.com", "AdminPass123!")
    csrf = cookies.get("emic_csrf")

    get_res = await ac.get("/api/user/site-selection", cookies=cookies)
    assert get_res.status_code == 200
    assert "accessibleSiteSlugs" in get_res.json()

    patch_res = await ac.patch(
        "/api/user/site-selection",
        cookies=cookies,
        headers={"X-CSRF-Token": csrf or ""},
        json={"selected_site_slugs": ["akarp"]},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["selectedSiteSlugs"] == ["akarp"]
    assert patch_res.json()["mode"] == "single"
