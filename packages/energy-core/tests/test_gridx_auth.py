"""GridX Auth0 password-realm authentication tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.gridx_auth import (
    fetch_gridx_token_set,
    gridx_token_needs_refresh,
    refresh_gridx_token_set,
)


def test_fetch_gridx_token_set_success():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "access.jwt.token",
        "refresh_token": "refresh-token",
        "expires_in": 86400,
    }
    with patch("energy_core.integrations.heartbeat.gridx_auth.httpx.post", return_value=response):
        token_set = fetch_gridx_token_set("user@example.com", "secret")
    assert token_set.access_token == "access.jwt.token"
    assert token_set.refresh_token == "refresh-token"


def test_fetch_gridx_token_set_missing_credentials():
    with pytest.raises(HeartbeatAuthError, match="username and password"):
        fetch_gridx_token_set("", "secret")


def test_fetch_gridx_token_set_auth_failure():
    response = MagicMock()
    response.status_code = 403
    response.json.return_value = {"error_description": "Wrong email or password"}
    with patch("energy_core.integrations.heartbeat.gridx_auth.httpx.post", return_value=response):
        with pytest.raises(HeartbeatAuthError, match="GridX login failed"):
            fetch_gridx_token_set("user@example.com", "wrong")


def test_refresh_gridx_token_set_success():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }
    with patch("energy_core.integrations.heartbeat.gridx_auth.httpx.post", return_value=response):
        token_set = refresh_gridx_token_set("old-refresh")
    assert token_set.access_token == "new-access"


def test_gridx_token_needs_refresh_empty():
    assert gridx_token_needs_refresh("") is True
