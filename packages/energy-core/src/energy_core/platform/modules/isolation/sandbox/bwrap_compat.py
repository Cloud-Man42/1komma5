"""Bubblewrap CLI capability probes (distro builds vary)."""

from __future__ import annotations

import subprocess
from functools import lru_cache


def _probe_option(bwrap_path: str, option: str) -> bool:
    result = subprocess.run(
        [
            bwrap_path,
            option,
            "--dev",
            "/dev",
            "--ro-bind",
            "/usr",
            "/usr",
            "true",
        ],
        capture_output=True,
        check=False,
    )
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    if "Unknown option" in stderr:
        return False
    return result.returncode == 0


@lru_cache(maxsize=8)
def bwrap_supports_no_new_privs(bwrap_path: str) -> bool:
    return _probe_option(bwrap_path, "--no-new-privs")


@lru_cache(maxsize=8)
def bwrap_supports_rlimit(bwrap_path: str) -> bool:
    result = subprocess.run(
        [
            bwrap_path,
            "--rlimit",
            "NOFILE",
            "64",
            "64",
            "--dev",
            "/dev",
            "--ro-bind",
            "/usr",
            "/usr",
            "true",
        ],
        capture_output=True,
        check=False,
    )
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    if "Unknown option" in stderr:
        return False
    return result.returncode == 0
