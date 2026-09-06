"""HeartBeat authentication surface."""

from __future__ import annotations

from energy_core.heartbeat_auth import (
    DEFAULT_REFRESH_SKEW_SECONDS,
    HeartbeatAuthError,
    fetch_bearer_token,
    refresh_bearer_token,
    token_needs_refresh,
)

__all__ = [
    "DEFAULT_REFRESH_SKEW_SECONDS",
    "HeartbeatAuthError",
    "fetch_bearer_token",
    "refresh_bearer_token",
    "token_needs_refresh",
]
