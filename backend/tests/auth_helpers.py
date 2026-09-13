"""Shared helpers for authenticated API tests."""

from __future__ import annotations

from httpx import AsyncClient


async def auth_login(ac: AsyncClient, username: str, password: str) -> dict:
    response = await ac.post("/api/auth/login", json={"username_or_email": username, "password": password})
    assert response.status_code == 200, response.text
    return response.cookies
