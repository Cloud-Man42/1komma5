#!/usr/bin/env python3
"""Launch bwrap directly and capture stderr."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "energy-core" / "src"))

from energy_core.config import Settings
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec
from energy_core.platform.modules.isolation.sandbox.linux_bwrap import LinuxBubblewrapLauncher


def main() -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_SANDBOX="bwrap",
    )
    package = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo"
    if not (package / "manifest.json").exists():
        import zipfile

        archive = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo-1.0.0.emicpkg"
        extract = Path("/tmp/sandbox-demo-pkg")
        extract.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extract)
        package = extract

    data = Path("/tmp/bwrap-debug-data")
    data.mkdir(exist_ok=True)
    socket = Path("/tmp/bwrap-debug.sock")
    bootstrap = ROOT / "scripts/isolated_runtime_bootstrap.py"
    sdk = ROOT / "packages/energy-core/src/emic_runtime_sdk"
    spec = SandboxLaunchSpec(
        runtime_instance_id="debug-runtime",
        module_id="integration.sandbox-demo",
        site_id=1,
        package_path=package,
        data_path=data,
        socket_path=socket,
        rpc_address=str(socket),
        startup_token="debug-token",
        artifact_sha256="0" * 64,
        version="1.0.0",
        bootstrap_script=bootstrap,
        sdk_path=sdk,
    )
    os.environ["EMIC_SANDBOX_MODE"] = "probe_uid"
    proc = LinuxBubblewrapLauncher(settings).launch(spec)
    time.sleep(2)
    rc = proc.process.poll()
    err = proc.process.stderr.read(16384) if proc.process.stderr else b""
    out = proc.process.stdout.read(16384) if proc.process.stdout else b""
    print("rc", rc)
    print("stderr", err.decode(errors="replace"))
    print("stdout", out.decode(errors="replace"))


if __name__ == "__main__":
    main()
