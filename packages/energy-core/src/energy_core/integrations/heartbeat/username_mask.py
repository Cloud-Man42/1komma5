"""Mask usernames for API responses — never expose full email."""

from __future__ import annotations


def mask_username(username: str) -> str:
    value = username.strip()
    if not value:
        return ""
    if "@" in value:
        local, domain = value.split("@", 1)
        if len(local) <= 1:
            masked_local = "*"
        else:
            masked_local = f"{local[0]}***"
        return f"{masked_local}@{domain}"
    if len(value) <= 2:
        return "*" * len(value)
    return f"{value[0]}***{value[-1]}"
