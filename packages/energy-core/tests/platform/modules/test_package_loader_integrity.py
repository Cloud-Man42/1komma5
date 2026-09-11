"""Installed package loader integrity must match installer checksum (Sprint E.5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from energy_core.config import Settings
from energy_core.db.models import Base, ModulePublisherKeyModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.modules.packages.installer import PackageInstaller
from energy_core.platform.modules.packages.loader import _verify_installed_package
from energy_core.platform.modules.packages.trust_store import PublisherTrustStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"
SENSIBO = FIXTURES / "integration.sensibo-1.0.0.emicpkg"
SIGNING = FIXTURES / "integration.sensibo-signing.json"


@pytest.mark.asyncio
async def test_sensibo_installed_package_passes_startup_verify(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL=f"sqlite+aiosqlite:///{tmp_path / 'pkg.db'}",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=False,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    info = json.loads(SIGNING.read_text(encoding="utf-8"))
    async with session_factory() as session:
        session.add(
            ModulePublisherKeyModel(
                publisher_id=str(info["publisher_id"]),
                key_id=str(info["key_id"]),
                public_key_hex=str(info["public_key_hex"]),
                status="trusted",
            )
        )
        await session.commit()
        result = await PackageInstaller(session, settings).install(SENSIBO)
        assert result.success, result.message
        from energy_core.db.installed_package_repo import InstalledPackageRepository

        row = await InstalledPackageRepository(session).get("integration.sensibo")
        assert row is not None
        verified = await _verify_installed_package(
            row,
            PublisherTrustStore(session),
            allow_unsigned=False,
        )
        assert verified is not None, "startup integrity verify must pass for signed Sensibo fixture"
    await engine.dispose()
