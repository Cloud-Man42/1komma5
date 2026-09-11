"""Fail-closed sandbox launcher tests."""

from __future__ import annotations

import sys

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox import SandboxUnavailableError, build_sandbox_launcher


def test_production_rejects_subprocess_sandbox():
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_SANDBOX="subprocess",
    )
    with pytest.raises(SandboxUnavailableError, match="not permitted in production"):
        build_sandbox_launcher(settings)


def test_bwrap_mode_without_binary_raises(monkeypatch):
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_SANDBOX="bwrap",
    )
    monkeypatch.setattr("energy_core.platform.modules.isolation.sandbox.shutil.which", lambda _: None)
    with pytest.raises(SandboxUnavailableError, match="bwrap"):
        build_sandbox_launcher(settings)


@pytest.mark.skipif(sys.platform == "win32", reason="dev subprocess allowed on Windows")
def test_development_allows_subprocess_on_linux():
    settings = Settings(
        _env_file=None,
        APP_ENV="development",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_SANDBOX="subprocess",
    )
    launcher = build_sandbox_launcher(settings)
    assert launcher.__class__.__name__ == "SubprocessSandboxLauncher"
