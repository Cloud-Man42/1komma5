"""The repo-wide guard must stop tests from reaching live services."""

from __future__ import annotations

import httpx
import pytest
import requests


def test_sync_httpx_request_is_blocked():
    with pytest.raises(RuntimeError, match="blocked"):
        httpx.get("https://api.open-meteo.com/v1/forecast")


async def test_async_httpx_request_is_blocked():
    async with httpx.AsyncClient() as ac:
        with pytest.raises(RuntimeError, match="blocked"):
            await ac.get("https://api.open-meteo.com/v1/forecast")


def test_requests_call_is_blocked():
    with pytest.raises(RuntimeError, match="blocked"):
        requests.get("https://api.myarcticspa.com/status", timeout=1)


async def test_in_process_transports_still_work():
    """Guarding sockets must not break the ASGI and mock transports the suite relies on."""
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/anything")
    assert res.json() == {"ok": True}
