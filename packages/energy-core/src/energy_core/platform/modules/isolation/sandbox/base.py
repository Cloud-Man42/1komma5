"""Sandbox launcher base types."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SandboxLaunchSpec:
    runtime_instance_id: str
    module_id: str
    site_id: int
    package_path: Path
    data_path: Path
    socket_path: Path
    rpc_address: str
    startup_token: str
    artifact_sha256: str
    version: str
    bootstrap_script: Path
    sdk_path: Path


@dataclass(frozen=True, slots=True)
class SandboxProcess:
    pid: int
    process: subprocess.Popen[bytes]
    sandbox_mode: str
    process_identity: str


class SandboxLauncher:
    def launch(self, spec: SandboxLaunchSpec) -> SandboxProcess:
        raise NotImplementedError

    def terminate(self, proc: SandboxProcess) -> None:
        if proc.process.poll() is None:
            proc.process.terminate()
            try:
                proc.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.process.kill()
