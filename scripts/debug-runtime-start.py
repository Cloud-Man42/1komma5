#!/usr/bin/env python3
"""Debug isolated runtime startup on Linux."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "energy-core" / "src"))

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.platform.modules.bootstrap import register_default_modules
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.types import RuntimeStartRequest
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import load_installed_module_packages
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def main() -> None:
    tmp = ROOT / ".tmp" / f"debug-runtime-{uuid.uuid4().hex[:8]}"
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
        ISOLATED_RUNTIME_STARTUP_TIMEOUT_SECONDS=20.0,
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    os.environ["EMIC_SANDBOX_MODE"] = "probe_uid"
    register_default_modules()
    archive = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo-1.0.0.emicpkg"
    async with session_factory() as session:
        from energy_core.db.models.module_publisher import ModulePublisherModel
        from energy_core.platform.modules.governance.types import PublisherTier
        from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
        from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore

        private_key, public_key = generate_ed25519_keypair()
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
        result = await PackageInstaller(session, settings).install(archive)
        assert result.success, result.message
        await load_installed_module_packages(session_factory, settings=settings)
        manager = IsolatedModuleRuntimeManager(session, settings)
        start = await manager.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
        print("start", start)
        print("listen", manager._gateway.listen_address())
        proc = manager._processes.get(start.runtime_instance_id or "")
        if proc is None and start.runtime_instance_id:
            proc = manager._processes.get(start.runtime_instance_id)
        if proc:
            print("poll", proc.process.poll())
            err = proc.process.stderr.read(65536) if proc.process.stderr else b""
            out = proc.process.stdout.read(65536) if proc.process.stdout else b""
            if err:
                print("stderr", err.decode(errors="replace"))
            if out:
                print("stdout", out.decode(errors="replace"))
        sock = manager._gateway.listen_address()
        if sock:
            p = Path(sock)
            print("socket exists", p.exists(), "mode", oct(p.stat().st_mode) if p.exists() else None)
        if start.ok:
            await manager.stop_runtime(start.runtime_instance_id)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
