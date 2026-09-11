#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "energy-core" / "src"))

from energy_core.config import Settings
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec
from energy_core.platform.modules.isolation.sandbox.linux_bwrap import LinuxBubblewrapLauncher
from energy_core.platform.modules.isolation.types import IsolatedRuntimeRecord


async def main() -> None:
    tmp = ROOT / ".tmp" / f"launch-debug-{uuid.uuid4().hex[:8]}"
    (tmp / "sockets").mkdir(parents=True)
    (tmp / "data").mkdir()
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        ISOLATED_RUNTIME_SANDBOX="bwrap",
    )
    runtime_id = uuid.uuid4().hex
    sock = tmp / "sockets" / f"{runtime_id}.sock"
    package_root = tmp / "pkg"
    package_root.mkdir()
    import zipfile

    archive = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo-1.0.0.emicpkg"
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(package_root)
    package = package_root
    print("manifest", (package / "manifest.json").exists())
    gateway = ModuleRpcGateway(settings)
    from energy_core.platform.modules.isolation.types import IsolatedRuntimeState

    record = IsolatedRuntimeRecord(
        id=1,
        runtime_instance_id=runtime_id,
        module_id="integration.sandbox-demo",
        version="1.0.0",
        publisher_id="emic-tests",
        artifact_sha256="0" * 64,
        site_id=1,
        state=IsolatedRuntimeState.PREPARING,
    )
    token = gateway.register_runtime(record, permissions=(), capabilities=())
    await gateway.start_server(str(sock))
    listen = gateway.listen_address()
    print("listen", listen, "exists", sock.exists())
    os.environ["EMIC_SANDBOX_MODE"] = "probe_uid"
    spec = SandboxLaunchSpec(
        runtime_instance_id=runtime_id,
        module_id="integration.sandbox-demo",
        site_id=1,
        package_path=package,
        data_path=tmp / "data",
        socket_path=sock,
        rpc_address=listen or str(sock),
        startup_token=token,
        artifact_sha256="0" * 64,
        version="1.0.0",
        bootstrap_script=ROOT / "scripts/isolated_runtime_bootstrap.py",
        sdk_path=ROOT / "packages/energy-core/src/emic_runtime_sdk",
    )
    proc = LinuxBubblewrapLauncher(settings).launch(spec)
    print("pid", proc.pid)
    for i in range(60):
        err = proc.process.stderr.read(4096) if proc.process.stderr else b""
        if err:
            print("stderr chunk", err.decode(errors="replace"))
        if proc.process.poll() is not None:
            print("exit", proc.process.returncode)
            break
        if gateway.session_store.has_active_session(runtime_id):
            print("session ok at", i * 0.25)
            break
        await asyncio.sleep(0.25)
    else:
        print("timeout poll", proc.process.poll())
    proc.process.kill()


if __name__ == "__main__":
    asyncio.run(main())
