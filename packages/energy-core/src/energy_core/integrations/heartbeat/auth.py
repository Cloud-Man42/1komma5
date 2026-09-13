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


def humanize_auth_error(message: str) -> str:
    """Turn raw Auth0/HTML login failures into short user-facing text."""
    text = message.strip()
    if text.startswith("HeartBeat login failed:"):
        text = text.split(":", 1)[1].strip()
    if "Login failed:" in text:
        text = text.split("Login failed:", 1)[1].strip()
    if "GridX login failed:" in text or "GridX token refresh failed:" in text:
        detail = text.split(":", 1)[-1].strip() if ":" in text else text
        return f"GridX-inloggning misslyckades: {detail[:200]}"
    if "Wrong email or password" in text:
        return (
            "Fel e-post eller lösenord för 1Komma5 Heartbeat. "
            "Testa samma uppgifter på https://my.1komma5.io först."
        )
    if "Log in to 1KOMMA5" in text or "Welcome" in text and "Heartbeat" in text:
        return (
            "1Komma5-inloggning misslyckades. Kontrollera e-post och lösenord "
            "(samma konto som på my.1komma5.io)."
        )
    if "<html" in text.lower() or "<!doctype" in text.lower():
        return (
            "1Komma5-inloggning misslyckades. Kontrollera e-post och lösenord "
            "(samma konto som på my.1komma5.io)."
        )
    return text[:512] if len(text) > 512 else text


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
