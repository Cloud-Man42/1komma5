"""Linux bubblewrap sandbox launcher."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec, SandboxLauncher, SandboxProcess
from energy_core.platform.modules.isolation.sandbox.bwrap_compat import (
    bwrap_supports_no_new_privs,
    bwrap_supports_rlimit,
)


class LinuxBubblewrapLauncher(SandboxLauncher):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _bwrap_path(self) -> str:
        override = os.environ.get("EMIC_BWRAP_PATH")
        if override:
            return override
        path = shutil.which("bwrap")
        if not path:
            raise RuntimeError("bubblewrap (bwrap) not available")
        return path

    def _host_bind_roots(self, python: Path) -> list[tuple[str, str]]:
        """Minimal host paths required to execute the interpreter (no /etc/home/root)."""
        roots: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add(host: Path, target: str | None = None) -> None:
            resolved = host.resolve()
            key = str(resolved)
            if not resolved.exists() or key in seen:
                return
            seen.add(key)
            mount = target or str(resolved)
            roots.append((key, mount))

        venv_root = python.parent.parent
        add(venv_root, str(venv_root))
        for lib_root in ("/lib", "/lib64", "/usr/lib", "/usr/lib64"):
            add(Path(lib_root), lib_root)
        return roots

    def launch(self, spec: SandboxLaunchSpec) -> SandboxProcess:
        bwrap = self._bwrap_path()
        uid = self._settings.isolated_runtime_module_uid
        gid = self._settings.isolated_runtime_module_gid
        spec.data_path.mkdir(parents=True, exist_ok=True)
        if os.geteuid() == 0:
            try:
                os.chown(spec.data_path, uid, gid)
            except OSError:
                pass
        package_path = spec.package_path.resolve()
        python = Path(sys.executable).resolve()
        memory_bytes = self._settings.isolated_runtime_memory_mb * 1024 * 1024
        cpu_limit = self._settings.isolated_runtime_cpu_time_limit_seconds
        use_bwrap_no_new_privs = bwrap_supports_no_new_privs(bwrap)
        use_bwrap_rlimit = bwrap_supports_rlimit(bwrap)
        cmd: list[str] = [
            bwrap,
            "--unshare-net",
            "--unshare-pid",
            "--die-with-parent",
            "--new-session",
        ]
        if use_bwrap_no_new_privs:
            cmd.append("--no-new-privs")
        launch_as_root = os.geteuid() == 0
        cmd.extend(["--tmpfs", "/tmp", "--chmod", "1777", "/tmp"])
        if not launch_as_root:
            cmd.extend(["--cap-drop", "ALL"])
        cmd.extend(
            [
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            "--ro-bind",
            str(package_path),
            "/package",
            "--bind",
            str(spec.data_path.resolve()),
            "/data",
            "--ro-bind",
            str(spec.bootstrap_script.resolve()),
            "/bootstrap.py",
            "--ro-bind",
            str(spec.sdk_path.resolve()),
            "/sdk",
            ]
        )
        for host, target in self._host_bind_roots(python):
            cmd.extend(["--ro-bind", host, target])
        rpc_address = spec.rpc_address
        if not rpc_address.startswith("tcp:"):
            socket_dir = Path(rpc_address).resolve().parent
            socket_dir.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--bind", str(socket_dir), str(socket_dir)])
        if use_bwrap_rlimit:
            cmd.extend(
                [
                    "--rlimit",
                    "AS",
                    str(memory_bytes),
                    str(memory_bytes),
                    "--rlimit",
                    "NPROC",
                    str(self._settings.isolated_runtime_max_processes),
                    str(self._settings.isolated_runtime_max_processes),
                    "--rlimit",
                    "NOFILE",
                    str(self._settings.isolated_runtime_max_open_files),
                    str(self._settings.isolated_runtime_max_open_files),
                    "--rlimit",
                    "CPU",
                    str(cpu_limit),
                    str(cpu_limit),
                ]
            )
        cmd.extend(
            [
                "--chdir",
                "/data",
                "--setenv",
                "EMIC_RPC_SOCKET",
                spec.rpc_address,
                "--setenv",
                "EMIC_RUNTIME_TOKEN",
                spec.startup_token,
                "--setenv",
                "EMIC_MODULE_ID",
                spec.module_id,
                "--setenv",
                "EMIC_SITE_ID",
                str(spec.site_id),
                "--setenv",
                "EMIC_RUNTIME_INSTANCE_ID",
                spec.runtime_instance_id,
                "--setenv",
                "EMIC_ARTIFACT_SHA256",
                spec.artifact_sha256,
                "--setenv",
                "EMIC_PROTOCOL_VERSION",
                str(self._settings.isolated_runtime_protocol_version),
                "--setenv",
                "EMIC_PACKAGE_PATH",
                "/package",
                "--setenv",
                "PYTHONPATH",
                "/sdk",
            ]
        )
        if not use_bwrap_no_new_privs:
            cmd.extend(["--setenv", "EMIC_SANDBOX_NO_NEW_PRIVS", "1"])
        if not use_bwrap_rlimit:
            cmd.extend(
                [
                    "--setenv",
                    "EMIC_SANDBOX_RLIMIT_AS",
                    str(memory_bytes),
                    "--setenv",
                    "EMIC_SANDBOX_RLIMIT_NPROC",
                    str(self._settings.isolated_runtime_max_processes),
                    "--setenv",
                    "EMIC_SANDBOX_RLIMIT_NOFILE",
                    str(self._settings.isolated_runtime_max_open_files),
                    "--setenv",
                    "EMIC_SANDBOX_RLIMIT_CPU",
                    str(cpu_limit),
                ]
            )
        if launch_as_root:
            cmd.extend(
                [
                    "--setenv",
                    "EMIC_SANDBOX_UID",
                    str(uid),
                    "--setenv",
                    "EMIC_SANDBOX_GID",
                    str(gid),
                ]
            )
        sandbox_mode = os.environ.get("EMIC_SANDBOX_MODE")
        if sandbox_mode:
            cmd.extend(["--setenv", "EMIC_SANDBOX_MODE", sandbox_mode])
        for env_key in (
            "EMIC_SANDBOX_FORCE_DROP_FAIL",
            "EMIC_HEARTBEAT_INTERVAL",
            "EMIC_PROBE_ROOT_READ_CANARY",
            "EMIC_PROBE_ROOT_WRITE_CANARY",
            "EMIC_SANDBOX_SKIP_HEARTBEAT",
            "EMIC_BROKER_ALLOW_URL",
            "EMIC_BROKER_OWN_SECRET",
            "EMIC_SENSIBO_FIXTURE_PODS",
        ):
            env_value = os.environ.get(env_key)
            if env_value:
                cmd.extend(["--setenv", env_key, env_value])
        cmd.extend([str(python), "-I", "-s", "/bootstrap.py"])
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        identity = f"uid:{uid};gid:{gid};sandbox:bwrap"
        return SandboxProcess(pid=proc.pid, process=proc, sandbox_mode="bwrap", process_identity=identity)
