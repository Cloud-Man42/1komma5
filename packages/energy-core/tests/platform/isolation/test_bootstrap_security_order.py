"""Bootstrap security ordering tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
BOOTSTRAP = REPO_ROOT / "scripts" / "isolated_runtime_bootstrap.py"


def test_bootstrap_security_order():
    source = BOOTSTRAP.read_text(encoding="utf-8")
    main_block = source.split("def main()")[1]
    handshake = main_block.index('"Handshake"')
    drop = main_block.index("_drop_module_identity()")
    bootstrap_ready = main_block.index('"BootstrapReady"')
    verify = main_block.index("_verify_effective_identity()")
    hardening = main_block.index("_apply_sandbox_hardening()")
    load_module = main_block.index("_load_module_entry(")
    report_module_ready = main_block.index('"ReportModuleReady"')
    assert handshake < hardening < drop < verify < bootstrap_ready < load_module < report_module_ready


def test_bootstrap_defines_privilege_drop_error():
    spec = importlib.util.spec_from_file_location("isolated_runtime_bootstrap", BOOTSTRAP)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "PrivilegeDropError")
