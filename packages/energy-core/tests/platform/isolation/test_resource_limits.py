"""Resource limit containment tests."""

from __future__ import annotations

import sys

import pytest

from energy_core.config import Settings


def test_resource_defaults_are_bounded():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    assert settings.isolated_runtime_memory_mb > 0
    assert settings.isolated_runtime_rpc_max_bytes > 0
    assert settings.isolated_runtime_rpc_rate_limit_per_minute > 0
    assert settings.isolated_runtime_startup_timeout_seconds >= 5.0


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="prlimit/cgroup enforcement is Linux-only")
def test_linux_resource_limits_documented_in_security_matrix():
    """Full fork/OOM adversarial cases run in Linux CI (see EMIC_RUNTIME_ISOLATION_SECURITY.md)."""
    assert sys.platform != "win32"
