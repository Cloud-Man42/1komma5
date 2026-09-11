"""Sandbox launcher tests (OS-level on Linux only)."""

from __future__ import annotations

import sys

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox import build_sandbox_launcher


def test_build_sandbox_launcher_mode():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    if sys.platform == "win32":
        settings = settings.model_copy(update={"isolated_runtime_sandbox": "subprocess"})
        launcher = build_sandbox_launcher(settings)
        assert launcher.__class__.__name__ == "SubprocessSandboxLauncher"
    else:
        settings = settings.model_copy(update={"isolated_runtime_sandbox": "bwrap"})
        launcher = build_sandbox_launcher(settings)
        assert launcher.__class__.__name__ == "LinuxBubblewrapLauncher"


@pytest.mark.integration
@pytest.mark.skipif(sys.platform == "win32", reason="bubblewrap OS sandbox is Linux-only")
def test_bwrap_binary_available():
    import shutil

    assert shutil.which("bwrap") is not None
