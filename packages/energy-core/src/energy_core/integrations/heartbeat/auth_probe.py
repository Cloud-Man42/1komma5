"""Probe 1KOMMA5 backends to auto-detect provider from username/password."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.integrations.heartbeat.auth import (
    HeartbeatAuthError,
    fetch_bearer_token,
    humanize_auth_error,
    jwt_expires_at,
)
from energy_core.integrations.heartbeat.connection import (
    CLOUD_PORT,
    DEFAULT_API_PATH,
    HeartbeatConnectionType,
    apply_provider_defaults,
    build_account_api_url,
)
from energy_core.integrations.heartbeat.gridx_auth import fetch_gridx_token_set
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider


@dataclass(frozen=True, slots=True)
class AuthProbeResult:
    provider: str
    connection_type: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    auth_domain: str
    auth_realm: str
    auth_client_id: str
    api_url: str | None
    access_token: str
    refresh_token: str | None
    token_expires_at: datetime | None
    probe_path: str
    probe_ok: bool


def _token_expires_at(token: str) -> datetime | None:
    exp = jwt_expires_at(token)
    return datetime.fromtimestamp(exp, tz=UTC) if exp else None


async def _probe_onekommafive(username: str, password: str) -> AuthProbeResult:
    token = await asyncio.to_thread(fetch_bearer_token, username, password)
    provider = HeartbeatBackendProvider.ONEKOMMAFIVE.value
    host, port, api_path, auth_domain, auth_realm, auth_client_id = apply_provider_defaults(provider)
    api_url = build_account_api_url(
        provider,
        HeartbeatConnectionType.CLOUD.value,
        host=host,
        port=port,
        use_tls=True,
        api_path=api_path,
    )
    return AuthProbeResult(
        provider=provider,
        connection_type=HeartbeatConnectionType.CLOUD.value,
        host=host,
        port=port or CLOUD_PORT,
        use_tls=True,
        api_path=api_path or DEFAULT_API_PATH,
        auth_domain=auth_domain,
        auth_realm=auth_realm,
        auth_client_id=auth_client_id,
        api_url=api_url,
        access_token=token,
        refresh_token=None,
        token_expires_at=_token_expires_at(token),
        probe_path="onekommafive.login",
        probe_ok=True,
    )


async def _probe_gridx(username: str, password: str) -> AuthProbeResult:
    token_set = await asyncio.to_thread(fetch_gridx_token_set, username, password)
    provider = HeartbeatBackendProvider.GRIDX.value
    host, port, api_path, auth_domain, auth_realm, auth_client_id = apply_provider_defaults(provider)
    api_url = build_account_api_url(
        provider,
        HeartbeatConnectionType.CLOUD.value,
        host=host,
        port=port,
        use_tls=True,
        api_path=api_path,
    )
    probe_ok = False
    probe_path = "gridx.login"
    if api_url and token_set.access_token:
        import httpx

        try:
            response = await asyncio.to_thread(
                httpx.get,
                f"{api_url.rstrip('/')}/account",
                headers={"Authorization": f"Bearer {token_set.access_token}", "Accept": "application/json"},
                timeout=20.0,
            )
            probe_ok = response.status_code == 200
            probe_path = "/account"
        except Exception:
            probe_ok = False
    return AuthProbeResult(
        provider=provider,
        connection_type=HeartbeatConnectionType.CLOUD.value,
        host=host,
        port=port or CLOUD_PORT,
        use_tls=True,
        api_path=api_path,
        auth_domain=auth_domain,
        auth_realm=auth_realm,
        auth_client_id=auth_client_id,
        api_url=api_url,
        access_token=token_set.access_token,
        refresh_token=token_set.refresh_token,
        token_expires_at=_token_expires_at(token_set.access_token),
        probe_path=probe_path,
        probe_ok=probe_ok,
    )


async def probe_heartbeat_credentials(username: str, password: str) -> AuthProbeResult:
    """Try 1Komma5 login first, then GridX. Raises HeartbeatAuthError if both fail."""
    username = username.strip()
    password = password.strip()
    if not username or not password:
        raise HeartbeatAuthError("E-post och lösenord krävs för Heartbeat-inloggning.")

    onekommafive_error: str | None = None
    try:
        return await _probe_onekommafive(username, password)
    except HeartbeatAuthError as exc:
        onekommafive_error = str(exc)

    try:
        return await _probe_gridx(username, password)
    except HeartbeatAuthError as gridx_exc:
        combined = humanize_auth_error(onekommafive_error or "1Komma5 login failed")
        gridx_detail = humanize_auth_error(str(gridx_exc))
        raise HeartbeatAuthError(
            f"Inloggning misslyckades mot båda 1KOMMA5-backends. "
            f"1Komma5: {combined}. GridX: {gridx_detail}."
        ) from gridx_exc
