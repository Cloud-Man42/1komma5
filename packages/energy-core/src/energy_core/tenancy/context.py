"""Server-side tenant context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantContext:
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    tenant_display_name: str
    user_id: int
    tenant_user_id: int
    is_platform_admin: bool
    platform_roles: frozenset[str]
