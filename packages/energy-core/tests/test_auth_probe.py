"""Auth probe tests — auto-detect 1komma5 vs GridX backend."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.auth_probe import AuthProbeResult, probe_heartbeat_credentials
from energy_core.integrations.heartbeat.gridx_auth import GridXTokenSet
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider


def _gridx_probe() -> AuthProbeResult:
    return AuthProbeResult(
        provider=HeartbeatBackendProvider.GRIDX.value,
        connection_type="cloud",
        host="api.gridx.de",
        port=443,
        use_tls=True,
        api_path="",
        auth_domain="gridx.eu.auth0.com",
        auth_realm="1komma5grad-authentication-db",
        auth_client_id="client",
        api_url="https://api.gridx.de",
        access_token="gridx-token",
        refresh_token="refresh",
        token_expires_at=datetime.now(UTC),
        probe_path="/account",
        probe_ok=True,
    )


@pytest.mark.asyncio
async def test_probe_prefers_onekommafive():
    with patch(
        "energy_core.integrations.heartbeat.auth_probe._probe_onekommafive",
        new=AsyncMock(
            return_value=AuthProbeResult(
                provider=HeartbeatBackendProvider.ONEKOMMAFIVE.value,
                connection_type="cloud",
                host="heartbeat.1komma5grad.com",
                port=443,
                use_tls=True,
                api_path="/api",
                auth_domain="",
                auth_realm="",
                auth_client_id="",
                api_url="https://heartbeat.1komma5grad.com/api",
                access_token="jwt",
                refresh_token=None,
                token_expires_at=None,
                probe_path="onekommafive.login",
                probe_ok=True,
            ),
        ),
    ):
        result = await probe_heartbeat_credentials("user@example.com", "secret")
    assert result.provider == HeartbeatBackendProvider.ONEKOMMAFIVE.value


@pytest.mark.asyncio
async def test_probe_falls_back_to_gridx():
    with patch(
        "energy_core.integrations.heartbeat.auth_probe._probe_onekommafive",
        new=AsyncMock(side_effect=HeartbeatAuthError("1komma5 failed")),
    ), patch(
        "energy_core.integrations.heartbeat.auth_probe._probe_gridx",
        new=AsyncMock(return_value=_gridx_probe()),
    ):
        result = await probe_heartbeat_credentials("user@example.com", "secret")
    assert result.provider == HeartbeatBackendProvider.GRIDX.value


@pytest.mark.asyncio
async def test_probe_requires_credentials():
    with pytest.raises(HeartbeatAuthError):
        await probe_heartbeat_credentials("", "secret")


@pytest.mark.asyncio
async def test_probe_both_fail():
    with patch(
        "energy_core.integrations.heartbeat.auth_probe._probe_onekommafive",
        new=AsyncMock(side_effect=HeartbeatAuthError("1komma5 failed")),
    ), patch(
        "energy_core.integrations.heartbeat.auth_probe._probe_gridx",
        new=AsyncMock(side_effect=HeartbeatAuthError("GridX login failed: bad")),
    ):
        with pytest.raises(HeartbeatAuthError, match="båda"):
            await probe_heartbeat_credentials("user@example.com", "wrong")
