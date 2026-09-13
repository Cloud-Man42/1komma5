"""IDOR regression tests for site-scoped API routes."""

from __future__ import annotations

import pytest

from auth_helpers import auth_login as _login

DENIED_SITE = "summer-house-denmark"


@pytest.mark.asyncio
async def test_viewer_denied_other_site_vehicles(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{DENIED_SITE}/vehicles", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_denied_other_site_spa_status(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{DENIED_SITE}/spa/status", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_denied_other_site_solar_forecast(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get(f"/api/sites/{DENIED_SITE}/solar/forecast", cookies=cookies)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_viewer_can_read_own_site_vehicles(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/sites/akarp/vehicles", cookies=cookies)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_viewer_can_read_own_site_solar_config(auth_client) -> None:
    ac, _ = auth_client
    cookies = await _login(ac, "viewer@example.com", "ViewerPass123!")
    response = await ac.get("/api/sites/akarp/solar/config", cookies=cookies)
    assert response.status_code == 200
