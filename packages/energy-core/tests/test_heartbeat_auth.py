import base64
import json
import time
from unittest.mock import patch

import pytest

from energy_core.heartbeat_auth import (
    HeartbeatAuthError,
    fetch_bearer_token,
    jwt_expires_at,
    token_needs_refresh,
)


def _make_jwt(exp: int) -> str:
    header = base64.urlsafe_b64encode(b"{}").decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.signature"


def test_jwt_expires_at_reads_exp_claim():
    exp = int(time.time()) + 3600
    assert jwt_expires_at(_make_jwt(exp)) == exp


def test_token_needs_refresh_when_missing():
    assert token_needs_refresh("") is True


def test_token_needs_refresh_when_near_expiry():
    exp = int(time.time()) + 120
    assert token_needs_refresh(_make_jwt(exp), skew_seconds=300) is True


def test_token_needs_refresh_when_still_valid():
    exp = int(time.time()) + 7200
    assert token_needs_refresh(_make_jwt(exp), skew_seconds=300) is False


def test_token_needs_refresh_keeps_unparseable_token():
    assert token_needs_refresh("not-a-jwt") is False


def test_fetch_bearer_token_requires_credentials():
    with pytest.raises(HeartbeatAuthError, match="username and password"):
        fetch_bearer_token("", "secret")


@patch("onekommafive.Client")
def test_fetch_bearer_token_returns_client_token(mock_client_cls):
    mock_client_cls.return_value.get_token.return_value = "jwt-token"
    token = fetch_bearer_token("user@example.com", "secret")
    assert token == "jwt-token"
    mock_client_cls.assert_called_once_with("user@example.com", "secret")


@patch("onekommafive.Client")
def test_fetch_bearer_token_wraps_login_errors(mock_client_cls):
    mock_client_cls.return_value.get_token.side_effect = RuntimeError("auth failed")
    with pytest.raises(HeartbeatAuthError, match="login failed"):
        fetch_bearer_token("user@example.com", "secret")
