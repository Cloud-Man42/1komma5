"""HeartBeat OAuth token acquisition and expiry checks."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_REFRESH_SKEW_SECONDS = 300


class HeartbeatAuthError(Exception):
    """HeartBeat authentication or token refresh failed."""


def fetch_bearer_token(username: str, password: str) -> str:
    """Obtain a Bearer token from 1Komma5 using email/password."""
    try:
        from onekommafive import Client
    except ImportError as exc:
        raise HeartbeatAuthError("onekommafive package is required for HeartBeat login") from exc

    username = username.strip()
    password = password.strip()
    if not username or not password:
        raise HeartbeatAuthError("HeartBeat username and password are required for token refresh")

    try:
        token = Client(username, password).get_token()
    except Exception as exc:
        raise HeartbeatAuthError(f"HeartBeat login failed: {exc}") from exc

    if not token:
        raise HeartbeatAuthError("HeartBeat login returned an empty token")
    return token


def jwt_expires_at(token: str) -> int | None:
    """Return JWT exp claim as unix timestamp, or None if unavailable."""
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload + padding)
        data: dict[str, Any] = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None
    exp = data.get("exp")
    if isinstance(exp, (int, float)):
        return int(exp)
    return None


def token_needs_refresh(token: str, *, skew_seconds: int = DEFAULT_REFRESH_SKEW_SECONDS) -> bool:
    """True when token is missing or close to expiry."""
    if not token:
        return True
    exp = jwt_expires_at(token)
    if exp is None:
        return False
    return time.time() >= exp - skew_seconds


async def refresh_bearer_token(username: str, password: str) -> str:
    """Fetch a Bearer token without blocking the event loop."""
    return await asyncio.to_thread(fetch_bearer_token, username, password)
