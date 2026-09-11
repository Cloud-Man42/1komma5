#!/usr/bin/env python3
"""Debug isolated runtime bwrap startup on Linux."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "energy-core" / "src"))


async def main() -> None:
    from energy_core.config import Settings
    from energy_core.db.models import Base
    from energy_core.db.models.module_publisher import ModulePublisherModel
    from energy_core.platform.modules.bootstrap import register_default_modules
    from energy_core.platform.modules.governance.types import PublisherTier
    from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
    from energy_core.platform.modules.isolation.types import RuntimeStartRequest
    from energy_core.platform.modules.packages.installer import PackageInstaller
    from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
    from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:////tmp/isolation-debug-{os.getpid()}.db",
        EMIC_MODULES_PATH="/tmp/isolation-modules",
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        ISOLATED_RUNTIME_ENABLED=True,
        THIRD_PARTY_RUNTIME_ENABLED=True,
        ISOLATED_RUNTIME_SANDBOX="bwrap",
        ISOLATED_RUNTIME_SOCKET_DIR="/tmp/runtime-sockets",
        ISOLATED_RUNTIME_DATA_ROOT="/tmp/runtime-data",
        ISOLATED_RUNTIME_STARTUP_TIMEOUT_SECONDS=15.0,
    )
    engine = create_async_engine(settings.database_url)
    sf = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    register_default_modules()
    async with sf() as session:
        _, pub = generate_ed25519_keypair()
        PublisherTrustStore(session).register_memory_key(
            PublisherKeyRecord(publisher_id="emic-tests", key_id="k1", public_key=pub, status=PublisherKeyStatus.TRUSTED)
        )
        session.add(
            ModulePublisherModel(
                publisher_id="emic-tests", display_name="T", tier=PublisherTier.VERIFIED.value, status="ACTIVE"
            )
        )
        await session.commit()
        archive = ROOT / "packages/energy-core/tests/fixtures/modules/integration.sandbox-demo-1.0.0.emicpkg"
        await PackageInstaller(session, settings).install(archive)
        await session.commit()
        from energy_core.platform.modules.packages.loader import load_installed_module_packages

        await load_installed_module_packages(sf, settings=settings)
        os.environ["EMIC_SANDBOX_MODE"] = "probe_uid"
        mgr = IsolatedModuleRuntimeManager(session, settings)
        bootstrap = mgr._resolve_bootstrap_script()
        print("bootstrap", bootstrap, bootstrap.exists())
        result = await mgr.start_runtime(RuntimeStartRequest(module_id="integration.sandbox-demo", site_id=1))
        print("result", result)
        if result.runtime_instance_id:
            proc = mgr.active_process(result.runtime_instance_id)
            if proc is None:
                print("no active process")
            else:
                import time
                time.sleep(0.5)
                err = proc.process.stderr.read(8192) if proc.process.stderr else b""
                out = proc.process.stdout.read(8192) if proc.process.stdout else b""
                print("stderr", err.decode(errors="replace"))
                print("stdout", out.decode(errors="replace"))
                print("poll", proc.process.poll())
            await mgr.stop_runtime(result.runtime_instance_id)


if __name__ == "__main__":
    asyncio.run(main())
