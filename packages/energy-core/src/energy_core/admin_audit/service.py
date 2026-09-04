"""Admin audit helpers."""

from __future__ import annotations

import json
from typing import Any

from energy_core.admin_audit.repo import AdminAuditRepository
from sqlalchemy.ext.asyncio import AsyncSession

_REDACT_KEYS = {
    "password",
    "api_token",
    "api_key",
    "chargeamps_api_key",
    "token",
    "emic_admin_token",
    "heartbeat_api_token",
}


def redact_summary(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        if key.lower() in _REDACT_KEYS:
            redacted[key] = "[redacted]"
        elif isinstance(value, dict):
            nested = redact_summary(value)
            redacted[key] = nested or {}
        else:
            redacted[key] = value
    return redacted


async def record_admin_audit(
    session: AsyncSession,
    *,
    http_method: str,
    path: str,
    action: str,
    outcome: str = "success",
    site_slug: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    repo = AdminAuditRepository(session)
    await repo.append(
        http_method=http_method,
        path=path,
        action=action,
        outcome=outcome,
        site_slug=site_slug,
        resource_type=resource_type,
        resource_id=resource_id,
        summary=redact_summary(summary),
    )


def parse_summary_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
