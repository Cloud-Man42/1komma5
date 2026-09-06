"""Tesla Fleet API configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TeslaConnectionInfo:
    region: str
    client_id_configured: bool
    client_secret_configured: bool
    refresh_token_configured: bool
    mock: bool
    ready: bool
    notes: tuple[str, ...]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def fleet_api_base_url(region: str) -> str:
    normalized = region.strip().lower()
    if normalized in {"na", "north america", "north_america", "us"}:
        return "https://fleet-api.prd.na.vn.cloud.tesla.com"
    return "https://fleet-api.prd.eu.vn.cloud.tesla.com"


def build_tesla_connection_info(
    *,
    region: str = "Europe",
    client_id: str | None = None,
    client_secret: str | None = None,
    refresh_token: str | None = None,
) -> TeslaConnectionInfo:
    resolved_client_id = client_id or os.getenv("TESLA_CLIENT_ID", "").strip() or None
    resolved_client_secret = client_secret or os.getenv("TESLA_CLIENT_SECRET", "").strip() or None
    resolved_refresh_token = refresh_token or os.getenv("TESLA_REFRESH_TOKEN", "").strip() or None
    mock = _env_bool("TESLA_MOCK", default=True)

    notes: list[str] = []
    if mock:
        notes.append("TESLA_MOCK är aktiv — mock-klient används.")
    if not resolved_client_id:
        notes.append("TESLA_CLIENT_ID saknas.")
    if not resolved_client_secret:
        notes.append("TESLA_CLIENT_SECRET saknas.")
    if not resolved_refresh_token:
        notes.append("Tesla refresh token saknas.")

    ready = bool(
        resolved_client_id
        and resolved_client_secret
        and resolved_refresh_token
        and not mock
    )
    return TeslaConnectionInfo(
        region=region,
        client_id_configured=bool(resolved_client_id),
        client_secret_configured=bool(resolved_client_secret),
        refresh_token_configured=bool(resolved_refresh_token),
        mock=mock,
        ready=ready,
        notes=tuple(notes),
    )
