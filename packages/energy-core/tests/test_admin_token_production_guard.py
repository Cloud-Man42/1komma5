"""Production guard for EMIC_ADMIN_TOKEN."""

from __future__ import annotations

import pytest

from energy_core.config import assert_emic_admin_token_production_safe


def test_production_guard_rejects_empty_token() -> None:
    with pytest.raises(RuntimeError, match="EMIC_ADMIN_TOKEN"):
        assert_emic_admin_token_production_safe(
            app_env="production",
            emic_admin_token="",
            emic_user_auth_enabled=False,
        )


def test_production_guard_rejects_whitespace_token() -> None:
    with pytest.raises(RuntimeError, match="EMIC_ADMIN_TOKEN"):
        assert_emic_admin_token_production_safe(
            app_env="production",
            emic_admin_token="   ",
            emic_user_auth_enabled=False,
        )


def test_production_guard_accepts_nonempty_token() -> None:
    assert_emic_admin_token_production_safe(app_env="production", emic_admin_token="secret-token")


def test_non_production_allows_empty_token() -> None:
    assert_emic_admin_token_production_safe(app_env="test", emic_admin_token="")
    assert_emic_admin_token_production_safe(app_env="development", emic_admin_token="")
