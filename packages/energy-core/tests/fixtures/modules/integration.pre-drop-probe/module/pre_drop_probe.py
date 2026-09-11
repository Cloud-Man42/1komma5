"""Pre-drop adversarial probe module."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _write_probes(results: dict[str, str]) -> None:
    Path("/data/probes.json").write_text(json.dumps(results, sort_keys=True), encoding="utf-8")


def _identity_probe() -> dict[str, str]:
    groups = os.getgroups() if hasattr(os, "getgroups") else []
    return {
        "uid": str(os.getuid()),
        "euid": str(os.geteuid()),
        "gid": str(os.getgid()),
        "egid": str(os.getegid()),
        "groups": ",".join(str(g) for g in groups),
    }


def _try_read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            content = handle.read(64)
        return "allowed" if content else "empty"
    except OSError as exc:
        return f"denied:{exc.__class__.__name__}"


def _try_write(path: str) -> str:
    try:
        Path(path).write_text("probe", encoding="utf-8")
        return "allowed"
    except OSError as exc:
        return f"denied:{exc.__class__.__name__}"


def _privilege_regain_probe() -> dict[str, str]:
    results: dict[str, str] = {}
    for name, fn in (
        ("setuid0", lambda: os.setuid(0)),
        ("setgid0", lambda: os.setgid(0)),
    ):
        try:
            fn()
            results[name] = "allowed"
        except OSError as exc:
            results[name] = f"denied:{exc.__class__.__name__}"
    return results


class PreDropProbeRuntime:
    def __init__(self, ctx: dict) -> None:
        self._ctx = ctx
        self._mode = os.environ.get("EMIC_SANDBOX_MODE", "entrypoint")

    def start(self) -> None:
        if self._mode == "entrypoint":
            probes = _identity_probe()
            read_canary = os.environ.get("EMIC_PROBE_ROOT_READ_CANARY", "")
            if read_canary:
                probes["root_read_canary"] = _try_read(read_canary)
            write_canary = os.environ.get("EMIC_PROBE_ROOT_WRITE_CANARY", "")
            if write_canary:
                probes["root_write_canary"] = _try_write(write_canary)
            probes.update(_privilege_regain_probe())
            _write_probes(probes)
        elif self._mode == "force_package_import":
            import importlib.util

            init_file = Path("/package/module/__init__.py")
            spec = importlib.util.spec_from_file_location("pre_drop_init", init_file)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            init_probe = Path("/data/init_probe.json")
            probes = {"init_imported": "yes" if init_probe.exists() else "no"}
            if init_probe.exists():
                probes.update(json.loads(init_probe.read_text(encoding="utf-8")))
            _write_probes(probes)


def build_module(ctx: dict):
    return PreDropProbeRuntime(ctx)
