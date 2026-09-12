"""Derive Heartbeat account health status from persisted audit fields."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HeartbeatAccountHealth(StrEnum):
    HEALTHY = "Healthy"
    DEGRADED = "Degraded"
    AUTHENTICATION_FAILED = "AuthenticationFailed"
    DISABLED = "Disabled"
    NOT_CONFIGURED = "NotConfigured"


@dataclass(frozen=True, slots=True)
class HeartbeatAccountHealthView:
    status: HeartbeatAccountHealth
    linked_sites_count: int = 0


def derive_account_health(
    *,
    is_enabled: bool,
    password_configured: bool,
    username: str,
    last_authentication_error: str | None,
    last_successful_authentication_at,
    last_successful_api_call_at,
    linked_sites_count: int = 0,
) -> HeartbeatAccountHealthView:
    if not is_enabled:
        return HeartbeatAccountHealthView(
            status=HeartbeatAccountHealth.DISABLED,
            linked_sites_count=linked_sites_count,
        )
    if not username.strip() or not password_configured:
        return HeartbeatAccountHealthView(
            status=HeartbeatAccountHealth.NOT_CONFIGURED,
            linked_sites_count=linked_sites_count,
        )
    if last_authentication_error and not last_successful_authentication_at:
        return HeartbeatAccountHealthView(
            status=HeartbeatAccountHealth.AUTHENTICATION_FAILED,
            linked_sites_count=linked_sites_count,
        )
    if last_authentication_error and not last_successful_api_call_at:
        return HeartbeatAccountHealthView(
            status=HeartbeatAccountHealth.DEGRADED,
            linked_sites_count=linked_sites_count,
        )
    if last_authentication_error:
        return HeartbeatAccountHealthView(
            status=HeartbeatAccountHealth.DEGRADED,
            linked_sites_count=linked_sites_count,
        )
    return HeartbeatAccountHealthView(
        status=HeartbeatAccountHealth.HEALTHY,
        linked_sites_count=linked_sites_count,
    )
