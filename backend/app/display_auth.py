"""Authentication for the display API (Raspberry Pi kiosk and enrolled browsers)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Annotated

from app.deps import get_app_settings, get_db_session
from app.widget_auth import AuthenticatedWidgetDevice, _parse_scopes
from energy_core.auth.device_tokens import extract_lookup_prefix, verify_token
from energy_core.config import Settings
from energy_core.db.apple_device_repo import AppleDeviceRepository
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

_bearer = HTTPBearer(auto_error=False)

DISPLAY_COOKIE_NAME = "emic_display_token"
DISPLAY_COOKIE_MAX_AGE_SECONDS = 365 * 24 * 60 * 60


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


def extract_display_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    """The Pi's local proxy injects a bearer header; other browsers send a cookie."""
    if credentials is not None and credentials.scheme.lower() == "bearer":
        header_token = credentials.credentials.strip()
        if header_token:
            return header_token
    cookie_token = (request.cookies.get(DISPLAY_COOKIE_NAME) or "").strip()
    return cookie_token or None


async def authenticate_display_token(
    token: str,
    session: AsyncSession,
) -> AuthenticatedWidgetDevice:
    """Resolve a display token to its device, raising 401 or 403 otherwise.

    Shared with enrollment so a cookie can never be issued for a token that the
    overview endpoint would go on to reject.
    """
    prefix = extract_lookup_prefix(token)
    if prefix is None:
        raise _unauthorized()

    repo = AppleDeviceRepository(session)
    row = await repo.get_by_prefix(prefix)
    if row is None or not verify_token(token, row.token_hash):
        raise _unauthorized()
    if row.revoked_at is not None:
        raise _unauthorized()

    if "display.read" not in _parse_scopes(row.scopes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return AuthenticatedWidgetDevice(record=repo._to_record(row), model=row)


class DisplayRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[int, deque[float]] = defaultdict(deque)

    def check(self, device_id: int, *, limit_per_minute: int) -> int | None:
        now = time.monotonic()
        window = self._windows[device_id]
        cutoff = now - 60.0
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit_per_minute:
            return max(1, int(60 - (now - window[0])))
        window.append(now)
        return None


DISPLAY_RATE_LIMITER = DisplayRateLimiter()


async def require_display_device(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AuthenticatedWidgetDevice:
    token = extract_display_token(request, credentials)
    if token is None:
        raise _unauthorized()

    device = await authenticate_display_token(token, session)
    record = device.record

    retry_after = DISPLAY_RATE_LIMITER.check(
        record.id,
        limit_per_minute=max(settings.widget_rate_limit_per_minute, 30),
    )
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    request.state.display_device_id = record.id
    await AppleDeviceRepository(session).touch_last_seen(record.id)
    await session.commit()
    return device
