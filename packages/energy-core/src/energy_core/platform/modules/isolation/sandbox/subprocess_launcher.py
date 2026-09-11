"""Development subprocess launcher (non-production sandbox)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec, SandboxLauncher, SandboxProcess


class SubprocessSandboxLauncher(SandboxLauncher):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def launch(self, spec: SandboxLaunchSpec) -> SandboxProcess:
        spec.data_path.mkdir(parents=True, exist_ok=True)
        env = {
            "EMIC_RPC_SOCKET": spec.rpc_address,
            "EMIC_RUNTIME_TOKEN": spec.startup_token,
            "EMIC_MODULE_ID": spec.module_id,
            "EMIC_SITE_ID": str(spec.site_id),
            "EMIC_RUNTIME_INSTANCE_ID": spec.runtime_instance_id,
            "EMIC_ARTIFACT_SHA256": spec.artifact_sha256,
            "EMIC_PROTOCOL_VERSION": str(self._settings.isolated_runtime_protocol_version),
            "EMIC_PACKAGE_PATH": str(spec.package_path.resolve()),
            "PYTHONPATH": str(spec.sdk_path.resolve()),
        }
        for key in ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "TEMP", "TMP", "USERPROFILE", "COMSPEC"):
            value = os.environ.get(key)
            if value:
                env[key] = value
        sandbox_mode = os.environ.get("EMIC_SANDBOX_MODE")
        if sandbox_mode:
            env["EMIC_SANDBOX_MODE"] = sandbox_mode
        for env_key in (
            "EMIC_SANDBOX_FORCE_DROP_FAIL",
            "EMIC_SANDBOX_UID",
            "EMIC_SANDBOX_GID",
            "EMIC_HEARTBEAT_INTERVAL",
            "EMIC_PROBE_ROOT_READ_CANARY",
            "EMIC_PROBE_ROOT_WRITE_CANARY",
            "EMIC_SANDBOX_SKIP_HEARTBEAT",
        ):
            value = os.environ.get(env_key)
            if value:
                env[env_key] = value
        python_args = [sys.executable, "-I", str(spec.bootstrap_script.resolve())]
        if sys.platform != "win32":
            python_args.insert(2, "-s")
        proc = subprocess.Popen(
            python_args,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(spec.data_path),
        )
        return SandboxProcess(
            pid=proc.pid,
            process=proc,
            sandbox_mode="subprocess",
            process_identity=f"pid:{proc.pid};sandbox:subprocess",
        )
