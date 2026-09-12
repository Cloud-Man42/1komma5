"""Authenticated principal for EMIC requests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from energy_core.auth.permissions import PERMISSION_ALL, permission_grants


class AuthMethod(StrEnum):
    SESSION = "session"
    BREAK_GLASS = "break_glass"
    LEGACY_OPEN = "legacy_open"


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: int | None
    username: str
    email: str
    display_name: str
    roles: frozenset[str]
    permissions: frozenset[str]
    site_ids: frozenset[int]
    auth_method: AuthMethod
    session_id: int | None = None
    must_change_password: bool = False

    def has_permission(self, permission: str) -> bool:
        return permission_grants(permission, self.permissions)

    def has_site_access(self, site_id: int) -> bool:
        if PERMISSION_ALL in self.permissions:
            return True
        return site_id in self.site_ids

    @property
    def is_super_admin(self) -> bool:
        return "SUPER_ADMIN" in self.roles or PERMISSION_ALL in self.permissions


def break_glass_principal() -> Principal:
    return Principal(
        user_id=None,
        username="break-glass",
        email="",
        display_name="Break-glass Admin",
        roles=frozenset({"SUPER_ADMIN"}),
        permissions=frozenset({PERMISSION_ALL}),
        site_ids=frozenset(),
        auth_method=AuthMethod.BREAK_GLASS,
    )


def legacy_open_principal() -> Principal:
    return Principal(
        user_id=None,
        username="legacy",
        email="",
        display_name="Legacy Open",
        roles=frozenset({"SUPER_ADMIN"}),
        permissions=frozenset({PERMISSION_ALL}),
        site_ids=frozenset(),
        auth_method=AuthMethod.LEGACY_OPEN,
    )
