"""Bootstrap sandbox hardening tests."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

resource = pytest.importorskip("resource")

REPO_ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = REPO_ROOT / "scripts" / "isolated_runtime_bootstrap.py"


def _load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("isolated_runtime_bootstrap", BOOTSTRAP)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(sys.platform != "linux", reason="rlimit hardening is Linux-only")
def test_apply_sandbox_hardening_sets_rlimits():
    mod = _load_bootstrap_module()
    env = {
        "EMIC_SANDBOX_RLIMIT_NOFILE": "48",
        "EMIC_SANDBOX_RLIMIT_NPROC": "8",
    }
    with patch.dict(os.environ, env, clear=False):
        mod._apply_sandbox_hardening()
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    assert soft == 48
    assert hard == 48
    soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
    assert soft == 8
    assert hard == 8
