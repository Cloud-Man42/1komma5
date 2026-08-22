"""Charge Amps connection info derived from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChargeAmpsConnectionInfo:
    provider: str
    effective_provider: str
    mock: bool
    api_key_configured: bool
    env_api_key_configured: bool
    charger_api_keys_configured: int
    email_configured: bool
    password_configured: bool
    ready: bool
    notes: tuple[str, ...]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_chargeamps_connection_info(*, charger_api_keys_configured: int = 0) -> ChargeAmpsConnectionInfo:
    provider = os.getenv("CHARGEAMPS_PROVIDER", "external").strip().lower() or "external"
    mock = _env_bool("CHARGEAMPS_MOCK", default=True)
    env_api_key_configured = bool(os.getenv("CHARGEAMPS_API_KEY", "").strip())
    api_key_configured = env_api_key_configured or charger_api_keys_configured > 0
    email_configured = bool(os.getenv("CHARGEAMPS_EMAIL", "").strip())
    password_configured = bool(os.getenv("CHARGEAMPS_PASSWORD", "").strip())
    effective_provider = "external" if api_key_configured else provider

    notes: list[str] = []
    if mock:
        notes.append("CHARGEAMPS_MOCK är aktiv — ingen riktig Halo-styrning.")
    if effective_provider == "external" and not api_key_configured:
        notes.append("CHARGEAMPS_API_KEY saknas i miljövariabler och ingen per-laddbox-nyckel är sparad.")
    if effective_provider == "web" and (not email_configured or not password_configured):
        notes.append("CHARGEAMPS_EMAIL/PASSWORD saknas — web-API kan inte autentisera.")
    if provider == "web" and api_key_configured and effective_provider == "external":
        notes.append("Per-laddbox API-nyckel används — External API har företräde framför web-provider.")

    if mock:
        ready = False
    elif effective_provider == "web":
        ready = email_configured and password_configured
    else:
        ready = api_key_configured
    return ChargeAmpsConnectionInfo(
        provider=provider,
        effective_provider=effective_provider,
        mock=mock,
        api_key_configured=api_key_configured,
        env_api_key_configured=env_api_key_configured,
        charger_api_keys_configured=charger_api_keys_configured,
        email_configured=email_configured,
        password_configured=password_configured,
        ready=ready,
        notes=tuple(notes),
    )


def assert_chargeamps_production_safe(*, app_env: str) -> None:
    if app_env.lower() != "production":
        return
    info = build_chargeamps_connection_info()
    if info.mock:
        raise RuntimeError("CHARGEAMPS_MOCK must be false in production")
