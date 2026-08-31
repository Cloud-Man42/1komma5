"""Mercedes auth unit tests."""

from __future__ import annotations

import ast
import hashlib
import base64
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import httpx

from energy_core.vehicles.mercedes.auth.errors import MercedesTwoFactorUnsupported, MercedesAuthError
from energy_core.vehicles.mercedes.auth.login import (
    MercedesLoginFlow,
    _code_from_auth_redirect,
    _extract_code,
    is_token_expired,
)
from energy_core.vehicles.mercedes.auth.pkce import generate_pkce_pair


def test_pkce_challenge_is_s256_of_verifier():
    verifier, challenge = generate_pkce_pair()
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    expected = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    assert challenge == expected


def test_pkce_pair_is_unique():
    first = generate_pkce_pair()
    second = generate_pkce_pair()
    assert first != second


def test_token_expired_when_within_skew():
    assert is_token_expired({"expires_at": 100}) is True


def test_token_valid_when_far_in_future(monkeypatch):
    monkeypatch.setattr("energy_core.vehicles.mercedes.auth.login.time.time", lambda: 0)
    assert is_token_expired({"expires_at": 10_000}) is False


@pytest.mark.asyncio
async def test_two_factor_response_raises_clear_error():
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    flow._get_authorization_resume = AsyncMock(return_value="resume")
    flow._send_user_agent_info = AsyncMock()
    flow._submit_username = AsyncMock()
    flow._submit_password = AsyncMock(return_value={"result": "GOTO_LOGIN_OTP"})

    with pytest.raises(MercedesTwoFactorUnsupported):
        await flow.login("user@example.com", "secret")


def test_extract_code_from_rismycar_redirect():
    url = "rismycar://login-callback?code=abc123&state=xyz"
    assert _extract_code(url) == "abc123"


def test_extract_code_raises_when_missing():
    with pytest.raises(MercedesAuthError, match="Authorization code not found"):
        _extract_code("rismycar://login-callback?state=xyz")


def test_extract_code_raises_oauth_error():
    with pytest.raises(MercedesAuthError, match="OAuth error: access_denied"):
        _extract_code("rismycar://login-callback?error=access_denied")


def test_code_from_auth_redirect_resolves_relative_location():
    response = httpx.Response(
        302,
        headers={"location": "rismycar://login-callback?code=rel-code"},
        request=httpx.Request("POST", "https://id.mercedes-benz.com/as/resume"),
    )
    assert _code_from_auth_redirect(response, "https://id.mercedes-benz.com") == "rel-code"


@pytest.mark.asyncio
async def test_resume_authorization_reuses_login_client():
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    cookies = httpx.Cookies()
    cookies.set("CIAM.SESSION", "session-token", domain="id.mercedes-benz.com")
    async with httpx.AsyncClient(cookies=cookies) as client:
        seen_cookies = False

        async def capture_post(*args, **kwargs):
            nonlocal seen_cookies
            assert kwargs.get("follow_redirects") is False
            seen_cookies = "CIAM.SESSION" in client.cookies
            return httpx.Response(
                302,
                headers={"location": "rismycar://login-callback?code=auth-code-42"},
                request=httpx.Request("POST", args[0] if args else kwargs["url"]),
            )

        client.post = capture_post  # type: ignore[method-assign]
        code = await flow._resume_authorization(client, "/as/resume/test", "login-token")
    assert code == "auth-code-42"
    assert seen_cookies


def _mock_httpx(monkeypatch, handler):
    """Route every AsyncClient the login flow builds through `handler`."""
    requests: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    real_client = httpx.AsyncClient

    def factory(**kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(record), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return requests


def _token_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"access_token": "fresh-access", "refresh_token": "fresh-refresh", "expires_in": 3600},
        request=request,
    )


@pytest.mark.asyncio
async def test_token_refresh_returns_a_new_access_token(monkeypatch):
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    requests = _mock_httpx(monkeypatch, _token_response)

    token_info = await flow.refresh_access_token("old-refresh")

    assert token_info["access_token"] == "fresh-access"
    assert token_info["refresh_token"] == "fresh-refresh"
    assert token_info["expires_at"] > 0
    assert [r.url.path for r in requests] == ["/as/token.oauth2"]


@pytest.mark.asyncio
async def test_token_refresh_does_not_fetch_the_app_version(monkeypatch):
    """/v1/config needs the very Bearer token we are refreshing, so stay away."""
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    called = False

    async def explode(*args, **kwargs):
        nonlocal called
        called = True
        return False

    monkeypatch.setattr(flow._app_version, "refresh", explode)
    requests = _mock_httpx(monkeypatch, _token_response)

    await flow.refresh_access_token("old-refresh")

    assert called is False
    assert all("config" not in r.url.path for r in requests)


@pytest.mark.asyncio
async def test_token_refresh_keeps_the_old_refresh_token_when_mercedes_omits_it(monkeypatch):
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    _mock_httpx(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={"access_token": "fresh-access", "expires_in": 3600},
            request=request,
        ),
    )

    token_info = await flow.refresh_access_token("old-refresh")

    assert token_info["refresh_token"] == "old-refresh"


@pytest.mark.asyncio
async def test_token_refresh_raises_when_mercedes_rejects_the_refresh_token(monkeypatch):
    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    _mock_httpx(monkeypatch, lambda request: httpx.Response(400, json={}, request=request))

    with pytest.raises(MercedesAuthError, match="Token refresh failed: 400"):
        await flow.refresh_access_token("old-refresh")


@pytest.mark.asyncio
async def test_an_expired_store_refreshes_instead_of_failing(monkeypatch):
    """The whole integration stalled here: every call went through this path."""
    from energy_core.vehicles.mercedes.auth.token_store import (
        MercedesTokenBundle,
        MercedesTokenStore,
    )

    flow = MercedesLoginFlow(region="Europe", device_guid="device-123")
    store = MercedesTokenStore(login_flow=flow)
    store.load(
        MercedesTokenBundle(
            access_token="stale-access",
            refresh_token="old-refresh",
            expires_at=1,
            device_guid="device-123",
            session_id="SESSION-1",
        )
    )
    _mock_httpx(monkeypatch, _token_response)

    assert await store.get_valid_access_token() == "fresh-access"
    assert store.session_id == "SESSION-1"


def test_auth_modules_do_not_log_sensitive_names():
    root = Path(__file__).resolve().parents[2] / "src" / "energy_core" / "vehicles" / "mercedes"
    forbidden = {"access_token", "refresh_token", "password", "code_verifier"}
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"debug", "info", "warning", "error"}:
                    for arg in node.args:
                        if isinstance(arg, ast.Name) and arg.id in forbidden:
                            offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []
