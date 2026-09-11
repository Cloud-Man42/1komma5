"""Select sandbox launcher for platform."""

from __future__ import annotations

import shutil

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox.base import SandboxLauncher
from energy_core.platform.modules.isolation.sandbox.linux_bwrap import LinuxBubblewrapLauncher
from energy_core.platform.modules.isolation.sandbox.subprocess_launcher import SubprocessSandboxLauncher


class SandboxUnavailableError(RuntimeError):
    """Raised when production isolation cannot launch a hardened sandbox."""


def build_sandbox_launcher(settings: Settings) -> SandboxLauncher:
    mode = settings.resolved_isolated_runtime_sandbox()
    if mode == "subprocess":
        if settings.is_production:
            raise SandboxUnavailableError("subprocess sandbox is not permitted in production")
        return SubprocessSandboxLauncher(settings)
    if mode == "bwrap":
        if not shutil.which("bwrap"):
            raise SandboxUnavailableError("bubblewrap (bwrap) is required but not available")
        return LinuxBubblewrapLauncher(settings)
    raise SandboxUnavailableError(f"unknown isolated runtime sandbox mode: {mode}")
