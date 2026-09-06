"""Zaptec REST integration configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ZaptecConnectionInfo:
    charger_id: str | None
    installation_id: str | None
    username_configured: bool
    password_configured: bool
    mock: bool
    ready: bool
    notes: tuple[str, ...]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_zaptec_connection_info(
    *,
    charger_id: str | None = None,
    installation_id: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> ZaptecConnectionInfo:
    resolved_charger_id = charger_id or os.getenv("ZAPTEC_CHARGER_ID", "").strip() or None
    resolved_installation_id = (
        installation_id or os.getenv("ZAPTEC_INSTALLATION_ID", "").strip() or None
    )
    resolved_username = username or os.getenv("ZAPTEC_USERNAME", "").strip() or None
    resolved_password = password or os.getenv("ZAPTEC_PASSWORD", "").strip() or None
    mock = _env_bool("ZAPTEC_MOCK", default=True)

    notes: list[str] = []
    if mock:
        notes.append("ZAPTEC_MOCK är aktiv — mock-klient används.")
    if not resolved_charger_id:
        notes.append("Zaptec charger ID saknas.")
    if not resolved_username:
        notes.append("ZAPTEC_USERNAME saknas.")
    if not resolved_installation_id:
        notes.append("Zaptec installation ID saknas (krävs för strömstyrning).")

    if not resolved_password:
        notes.append("ZAPTEC_PASSWORD saknas.")

    ready = bool(resolved_charger_id and resolved_username and resolved_password and not mock)
    return ZaptecConnectionInfo(
        charger_id=resolved_charger_id,
        installation_id=resolved_installation_id,
        username_configured=bool(resolved_username),
        password_configured=bool(resolved_password),
        mock=mock,
        ready=ready,
        notes=tuple(notes),
    )
