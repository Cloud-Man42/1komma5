"""Optional Bearer admin token for sensitive configuration routes."""

from __future__ import annotations

from typing import Annotated

from app.deps import get_app_settings
from energy_core.config import Settings
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def require_admin_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> None:
    expected = (settings.emic_admin_token or "").strip()
    if not expected:
        return

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )
