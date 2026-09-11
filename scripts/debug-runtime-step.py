#!/usr/bin/env python3
"""Step-through runtime launch debug."""
from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "energy-core" / "src"))

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.governance.types import PublisherTier
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec
from energy_core.platform.modules.isolation.sandbox import build_sandbox_launcher
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    tmp = ROOT / ".tmp" / f"debug-step-{uuid.uuid4().hex[:8]}"
    tmp.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{(tmp / 'debug.db').as_posix()}",
        EMIC_MODULES_PATH=str(tmp / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        ISOLATED_RUNTIME_ENABLED=True,
        THIRD_PARTY_RUNTIME_ENABLED=True,
        ISOLATED_RUNTIME_SANDBOX="bwrap",
        ISOLATED_RUNTIME_SOCKET_DIR=str(tmp / "sockets"),
        ISOLATED_RUNTIME_DATA_ROOT=str(tmp / "runtime-data"),
    )
    os.environ["EMIC_SANDBOX_MODE"] = "probe_uid"
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    register_default_modules()
    archive = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo-1.0.0.emicpkg"
    async with session_factory() as session:
        _, public_key = generate_ed25519_keypair()
        PublisherTrustStore(session).register_memory_key(
            PublisherKeyRecord(
                publisher_id="emic-tests",
                key_id="test-1",
                public_key=public_key,
                status=PublisherKeyStatus.TRUSTED,
            )
        )
        session.add(
            ModulePublisherModel(
                publisher_id="emic-tests",
                display_name="Test Publisher",
                tier=PublisherTier.VERIFIED.value,
                status="ACTIVE",
            )
        )
        await session.commit()
        await PackageInstaller(session, settings).install(archive)
        await load_installed_module_packages(session_factory, settings=settings)
        manager = IsolatedModuleRuntimeManager(session, settings)
        from energy_core.platform.modules.isolation.types import RuntimeStartRequest

        req = RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1)
        package = await manager._packages.get_installed("integration.sandbox-demo")
        assert package is not None
        runtime_id = uuid.uuid4().hex
        socket_path = Path(settings.resolved_isolated_runtime_socket_dir()) / f"{runtime_id}.sock"
        data_path = Path(settings.resolved_isolated_runtime_data_root()) / "integration.sandbox-demo" / "1" / runtime_id
        record = await manager._repo.create(
            runtime_instance_id=runtime_id,
            module_id="integration.sandbox-demo",
            site_id=1,
            version=package.version,
            artifact_sha256=package.artifact_sha256,
        )
        token = manager._gateway.register_runtime(record, permissions=(), capabilities=())
        await manager._gateway.start_server(str(socket_path))
        listen = manager._gateway.listen_address()
        print("listen", listen)
        spec = SandboxLaunchSpec(
            runtime_instance_id=runtime_id,
            module_id="integration.sandbox-demo",
            site_id=1,
            package_path=Path(package.package_path),
            data_path=data_path,
            socket_path=socket_path,
            rpc_address=listen or str(socket_path),
            startup_token=token,
            artifact_sha256=package.artifact_sha256,
            version=package.version,
            bootstrap_script=manager._resolve_bootstrap_script(),
            sdk_path=manager._resolve_sdk_path(),
        )
        proc = build_sandbox_launcher(settings).launch(spec)
        print("pid", proc.pid)
        for i in range(40):
            if proc.process.poll() is not None:
                err = proc.process.stderr.read() if proc.process.stderr else b""
                print("exited", proc.process.returncode, err.decode(errors="replace"))
                break
            if manager._gateway.session_store.has_active_session(runtime_id):
                print("session active at", i * 0.25)
                break
            await asyncio.sleep(0.25)
        else:
            err = proc.process.stderr.read() if proc.process.stderr else b""
            print("timeout poll", proc.process.poll(), "stderr", err.decode(errors="replace"))
        sock = Path(listen or socket_path)
        print("socket exists", sock.exists())
        proc.process.kill()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
