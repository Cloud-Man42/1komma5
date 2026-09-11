"""Package import hook — records identity if imported."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _record(label: str) -> None:
    probe = Path("/data") / f"{label}_probe.json"
    payload = {
        "uid": os.getuid(),
        "euid": os.geteuid(),
        "gid": os.getgid(),
        "egid": os.getegid(),
    }
    probe.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


_record("init")
