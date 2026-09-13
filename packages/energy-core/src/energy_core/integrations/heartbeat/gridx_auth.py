"""GridX Auth0 password-realm login and refresh-token flow."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from energy_core.integrations.heartbeat.auth import HeartbeatAuthError, jwt_expires_at, token_needs_refresh
from energy_core.integrations.heartbeat.gridx_defaults import (
    GRIDX_AUTH_AUDIENCE,
    GRIDX_AUTH_CLIENT_ID,
    GRIDX_AUTH_DOMAIN,
    GRIDX_AUTH_REALM,
)

logger = logging.getLogger(__name__)

PASSWORD_REALM_GRANT = "http://auth0.com/oauth/grant-type/password-realm"


@dataclass(frozen=True, slots=True)
class GridXTokenSet:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None


def _token_url(auth_domain: str) -> str:
    domain = auth_domain.strip() or GRIDX_AUTH_DOMAIN
    if domain.startswith("http"):
        return f"{domain.rstrip('/')}/oauth/token"
    return f"https://{domain}/oauth/token"


def _parse_auth_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:512]
    if isinstance(payload, dict):
        description = payload.get("error_description") or payload.get("error") or payload.get("message")
        if description:
            return str(description)
    return response.text[:512]


def fetch_gridx_token_set(
    username: str,
    password: str,
    *,
    auth_domain: str = "",
    auth_realm: str = "",
    auth_client_id: str = "",
    audience: str = GRIDX_AUTH_AUDIENCE,
) -> GridXTokenSet:
    """Login via Auth0 password-realm grant (my.1komma5.io / GridX)."""
    username = username.strip()
    password = password.strip()
    if not username or not password:
        raise HeartbeatAuthError("GridX username and password are required")

    body: dict[str, Any] = {
        "grant_type": PASSWORD_REALM_GRANT,
        "username": username,
        "password": password,
        "realm": (auth_realm.strip() or GRIDX_AUTH_REALM),
        "client_id": (auth_client_id.strip() or GRIDX_AUTH_CLIENT_ID),
        "audience": audience,
        "scope": "openid profile email offline_access",
    }
    try:
        response = httpx.post(_token_url(auth_domain), json=body, timeout=30.0)
    except httpx.HTTPError as exc:
        raise HeartbeatAuthError(f"GridX login request failed: {exc}") from exc

    if response.status_code >= 400:
        raise HeartbeatAuthError(f"GridX login failed: {_parse_auth_error(response)}")

    data = response.json()
    access_token = str(data.get("access_token") or "")
    if not access_token:
        raise HeartbeatAuthError("GridX login returned an empty access token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in")
    return GridXTokenSet(
        access_token=access_token,
        refresh_token=str(refresh_token) if refresh_token else None,
        expires_in=int(expires_in) if isinstance(expires_in, (int, float)) else None,
    )


def refresh_gridx_token_set(
    refresh_token: str,
    *,
    auth_domain: str = "",
    auth_client_id: str = "",
) -> GridXTokenSet:
    """Refresh GridX access token using stored refresh token."""
    refresh_token = refresh_token.strip()
    if not refresh_token:
        raise HeartbeatAuthError("GridX refresh token is missing")

    body = {
        "grant_type": "refresh_token",
        "client_id": (auth_client_id.strip() or GRIDX_AUTH_CLIENT_ID),
        "refresh_token": refresh_token,
    }
    try:
        response = httpx.post(_token_url(auth_domain), json=body, timeout=30.0)
    except httpx.HTTPError as exc:
        raise HeartbeatAuthError(f"GridX token refresh request failed: {exc}") from exc

    if response.status_code >= 400:
        raise HeartbeatAuthError(f"GridX token refresh failed: {_parse_auth_error(response)}")

    data = response.json()
    access_token = str(data.get("access_token") or "")
    if not access_token:
        raise HeartbeatAuthError("GridX refresh returned an empty access token")
    new_refresh = data.get("refresh_token") or refresh_token
    expires_in = data.get("expires_in")
    return GridXTokenSet(
        access_token=access_token,
        refresh_token=str(new_refresh) if new_refresh else None,
        expires_in=int(expires_in) if isinstance(expires_in, (int, float)) else None,
    )


def gridx_token_needs_refresh(access_token: str, *, skew_seconds: int = 300) -> bool:
    """GridX JWTs expose exp; opaque tokens fall back to always refresh when empty."""
    if not access_token:
        return True
    if jwt_expires_at(access_token) is not None:
        return token_needs_refresh(access_token, skew_seconds=skew_seconds)
    return False


async def login_gridx_token_set(
    username: str,
    password: str,
    *,
    auth_domain: str = "",
    auth_realm: str = "",
    auth_client_id: str = "",
) -> GridXTokenSet:
    return await asyncio.to_thread(
        fetch_gridx_token_set,
        username,
        password,
        auth_domain=auth_domain,
        auth_realm=auth_realm,
        auth_client_id=auth_client_id,
    )


async def refresh_gridx_token_set_async(
    refresh_token: str,
    *,
    auth_domain: str = "",
    auth_client_id: str = "",
) -> GridXTokenSet:
    return await asyncio.to_thread(
        refresh_gridx_token_set,
        refresh_token,
        auth_domain=auth_domain,
        auth_client_id=auth_client_id,
    )
