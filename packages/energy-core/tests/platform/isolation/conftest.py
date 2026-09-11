"""Isolation test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.types import PublisherTier
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


async def register_test_publisher(session, *, publisher_id: str = "emic-tests", key_id: str = "test-1"):
    private_key, public_key = generate_ed25519_keypair()
    store = PublisherTrustStore(session)
    store.register_memory_key(
        PublisherKeyRecord(
            publisher_id=publisher_id,
            key_id=key_id,
            public_key=public_key,
            status=PublisherKeyStatus.TRUSTED,
        )
    )
    return store, private_key


@pytest.fixture
async def isolation_session(tmp_path):
    db_file = tmp_path / "isolation.db"
    import os

    socket_root = Path(f"/tmp/emic-rt-{os.getpid()}")
    socket_root.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
        ISOLATED_RUNTIME_ENABLED=True,
        THIRD_PARTY_RUNTIME_ENABLED=True,
        ISOLATED_RUNTIME_SANDBOX="subprocess",
        ISOLATED_RUNTIME_SOCKET_DIR=str(socket_root),
        ISOLATED_RUNTIME_DATA_ROOT=str(tmp_path / "runtime-data"),
        ISOLATED_RUNTIME_STARTUP_TIMEOUT_SECONDS=15.0,
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings, session_factory
    await engine.dispose()


@pytest.fixture
async def sandbox_demo_package(isolation_session):
    session, settings, session_factory = isolation_session
    build_script = FIXTURES / "integration.sandbox-demo" / "build_emicpkg.py"
    import subprocess
    import sys

    subprocess.run([sys.executable, str(build_script)], check=True)
    archive = FIXTURES / "integration.sandbox-demo-1.0.0.emicpkg"
    await register_test_publisher(session, publisher_id="emic-tests")
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
    assert result.success
    return session, settings, session_factory



@pytest.fixture
async def runtime_e2e_package(isolation_session, monkeypatch):
    from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine

    monkeypatch.setattr(ModuleInstallPolicyEngine, "CONTROL_ISOLATION_GATE_OPEN", True)
    session, settings, session_factory = isolation_session
    build_script = FIXTURES / "integration.runtime-e2e" / "build_emicpkg.py"
    import subprocess
    import sys

    subprocess.run([sys.executable, str(build_script)], check=True)
    archive = FIXTURES / "integration.runtime-e2e-1.0.0.emicpkg"
    await register_test_publisher(session, publisher_id="emic-tests")
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
    assert result.success
    return session, settings, session_factory


@pytest.fixture
async def pre_drop_probe_package(isolation_session):
    session, settings, session_factory = isolation_session
    build_script = FIXTURES / "integration.pre-drop-probe" / "build_emicpkg.py"
    import subprocess
    import sys

    subprocess.run([sys.executable, str(build_script)], check=True)
    archive = FIXTURES / "integration.pre-drop-probe-1.0.0.emicpkg"
    await register_test_publisher(session, publisher_id="emic-tests")
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
    assert result.success
    return session, settings, session_factory
