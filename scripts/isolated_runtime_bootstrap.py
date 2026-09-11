#!/usr/bin/env python3
"""Isolated third-party module worker bootstrap (Step 5C.5)."""

from __future__ import annotations

import errno
import importlib.util
import json
import os
import socket
import sys
import time
from pathlib import Path


class PrivilegeDropError(OSError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def _clear_supplementary_groups() -> None:
    if sys.platform != "linux":
        return
    if not hasattr(os, "setgroups"):
        return
    try:
        os.setgroups([])
    except OSError:
        pass


def _drop_module_identity() -> None:
    uid = os.environ.get("EMIC_SANDBOX_UID")
    gid = os.environ.get("EMIC_SANDBOX_GID")
    if not uid or not gid:
        return
    if os.geteuid() != 0:
        return
    forced = os.environ.get("EMIC_SANDBOX_FORCE_DROP_FAIL")
    if forced == "setgid":
        raise PrivilegeDropError("setgid", "forced setgid failure")
    if forced == "setuid":
        _clear_supplementary_groups()
        os.setgid(int(gid))
        raise PrivilegeDropError("setuid", "forced setuid failure")
    _clear_supplementary_groups()
    os.setgid(int(gid))
    os.setuid(int(uid))


def _verify_effective_identity() -> tuple[int, int]:
    if not os.environ.get("EMIC_SANDBOX_UID") or not hasattr(os, "getuid"):
        return -1, -1
    uid = os.getuid()
    gid = os.getgid()
    expected_uid = int(os.environ.get("EMIC_SANDBOX_UID", uid))
    expected_gid = int(os.environ.get("EMIC_SANDBOX_GID", gid))
    if os.environ.get("EMIC_SANDBOX_UID") and uid != expected_uid:
        raise PrivilegeDropError("verify", f"uid mismatch: {uid} != {expected_uid}")
    if os.environ.get("EMIC_SANDBOX_GID") and gid != expected_gid:
        raise PrivilegeDropError("verify", f"gid mismatch: {gid} != {expected_gid}")
    return uid, gid


def _apply_sandbox_hardening() -> None:
    """Apply limits that older distro bwrap builds omit from CLI."""
    if sys.platform != "linux":
        return
    if os.environ.get("EMIC_SANDBOX_NO_NEW_PRIVS") == "1":
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        pr_set_no_new_privs = 38
        if libc.prctl(pr_set_no_new_privs, 1, 0, 0, 0) != 0:
            raise RuntimeError("failed to set no_new_privs in sandbox worker")
    import resource

    limit_map = (
        ("EMIC_SANDBOX_RLIMIT_AS", resource.RLIMIT_AS),
        ("EMIC_SANDBOX_RLIMIT_NPROC", resource.RLIMIT_NPROC),
        ("EMIC_SANDBOX_RLIMIT_NOFILE", resource.RLIMIT_NOFILE),
        ("EMIC_SANDBOX_RLIMIT_CPU", resource.RLIMIT_CPU),
    )
    for env_key, rlimit in limit_map:
        raw = os.environ.get(env_key)
        if not raw:
            continue
        value = int(raw)
        resource.setrlimit(rlimit, (value, value))


def _load_module_entry(package_path: Path, entrypoint: str):
    manifest_path = package_path / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("manifest.json missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module_name, attr = entrypoint.split(":", 1)
    module_root = package_path / "module"
    module_root_str = str(module_root)
    if module_root.exists() and module_root_str not in sys.path:
        sys.path.insert(0, module_root_str)
    module_file = module_root / f"{module_name.replace('.', '/')}.py"
    if not module_file.exists():
        raise RuntimeError(f"module file missing: {module_file}")
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load module spec")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, attr), manifest


def _rpc_call(sock_path: str, method: str, params: dict, *, session_token: str | None = None) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    if session_token:
        payload["params"] = {**params, "_session_token": session_token}
    data = (json.dumps(payload) + "\n").encode("utf-8")
    if sock_path.startswith("tcp:"):
        _, host, port = sock_path.split(":", 2)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
    else:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(sock_path)
    try:
        sock.sendall(data)
        raw = sock.recv(65536).split(b"\n", 1)[0]
        response = json.loads(raw.decode("utf-8"))
    finally:
        sock.close()
    if "error" in response:
        raise RuntimeError(response["error"].get("message", "rpc error"))
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("invalid rpc result")
    return result


def _report_privilege_drop_failure(
    sock_path: str,
    *,
    session_token: str,
    runtime_instance_id: str,
    module_id: str,
    site_id: int,
    stage: str,
    reason: str,
) -> None:
    try:
        _rpc_call(
            sock_path,
            "ReportPrivilegeDropFailed",
            {
                "runtime_instance_id": runtime_instance_id,
                "module_id": module_id,
                "site_id": site_id,
                "stage": stage,
                "reason": reason,
            },
            session_token=session_token,
        )
    except Exception:
        pass


def main() -> None:
    sock_path = os.environ["EMIC_RPC_SOCKET"]
    startup_token = os.environ["EMIC_RUNTIME_TOKEN"]
    module_id = os.environ["EMIC_MODULE_ID"]
    runtime_instance_id = os.environ["EMIC_RUNTIME_INSTANCE_ID"]
    artifact_sha256 = os.environ["EMIC_ARTIFACT_SHA256"]
    protocol_version = int(os.environ.get("EMIC_PROTOCOL_VERSION", "1"))
    package_path = Path(os.environ.get("EMIC_PACKAGE_PATH", "/package"))

    manifest_path = package_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest.get("version", "0.0.0")
    entrypoint = manifest.get("entrypoint", "")
    site_id = int(os.environ.get("EMIC_SITE_ID") or manifest.get("test_site_id", 1))
    session_token: str | None = None
    try:
        handshake = _rpc_call(
            sock_path,
            "Handshake",
            {
                "startup_token": startup_token,
                "module_id": module_id,
                "version": version,
                "artifact_sha256": artifact_sha256,
                "runtime_instance_id": runtime_instance_id,
                "protocol_version": protocol_version,
                "site_id": site_id,
            },
        )
        session_token = handshake["session_token"]
        expected_uid = int(os.environ.get("EMIC_SANDBOX_UID", "0") or "0")
        expected_gid = int(os.environ.get("EMIC_SANDBOX_GID", "0") or "0")
        _apply_sandbox_hardening()
        _drop_module_identity()
        uid, gid = _verify_effective_identity()
        if expected_uid and uid >= 0 and (uid != expected_uid or gid != expected_gid):
            raise PrivilegeDropError("verify", f"identity mismatch after drop: uid={uid} gid={gid}")
        ready_params: dict = {
            "runtime_instance_id": runtime_instance_id,
            "module_id": module_id,
            "site_id": site_id,
        }
        if uid >= 0 and gid >= 0:
            ready_params["uid"] = uid
            ready_params["gid"] = gid
        _rpc_call(sock_path, "BootstrapReady", ready_params, session_token=session_token)
        runtime_factory, _ = _load_module_entry(package_path, entrypoint)
        runtime = runtime_factory(
            {
                "module_id": module_id,
                "site_id": site_id,
                "session_token": session_token,
                "runtime_instance_id": runtime_instance_id,
                "rpc_socket": sock_path,
            }
        )
        if hasattr(runtime, "start"):
            runtime.start()
        _rpc_call(
            sock_path,
            "ReportModuleReady",
            {
                "runtime_instance_id": runtime_instance_id,
                "module_id": module_id,
                "site_id": site_id,
            },
            session_token=session_token,
        )
    except PrivilegeDropError as exc:
        if session_token:
            _report_privilege_drop_failure(
                sock_path,
                session_token=session_token,
                runtime_instance_id=runtime_instance_id,
                module_id=module_id,
                site_id=site_id,
                stage=exc.stage,
                reason=str(exc),
            )
        sys.exit(1)
    except OSError as exc:
        if session_token and exc.errno in {errno.EPERM, errno.EACCES}:
            stage = "setuid" if "setuid" in str(exc).lower() else "setgid"
            _report_privilege_drop_failure(
                sock_path,
                session_token=session_token,
                runtime_instance_id=runtime_instance_id,
                module_id=module_id,
                site_id=site_id,
                stage=stage,
                reason=str(exc),
            )
        raise

    while True:
        if os.environ.get("EMIC_SANDBOX_SKIP_HEARTBEAT") != "1":
            _rpc_call(
                sock_path,
                "GetHealth",
                {
                    "runtime_instance_id": runtime_instance_id,
                    "module_id": module_id,
                    "site_id": site_id,
                },
                session_token=session_token,
            )
        if hasattr(runtime, "tick"):
            runtime.tick()
        time.sleep(float(os.environ.get("EMIC_HEARTBEAT_INTERVAL", "2")))


if __name__ == "__main__":
    main()
