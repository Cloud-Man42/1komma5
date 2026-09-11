"""Shared helpers for package tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.platform.modules.packages.signing import generate_ed25519_keypair, sign_package_dir
from energy_core.platform.modules.packages.trust_store import PublisherKeyRecord, PublisherKeyStatus, PublisherTrustStore

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "modules"


@pytest.fixture
async def package_session(tmp_path):
    db_file = tmp_path / "packages.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_MODULES_PATH=str(tmp_path / "modules"),
        EMIC_ALLOW_UNSIGNED_MODULES=True,
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings, session_factory
    await engine.dispose()


async def register_test_publisher(session: AsyncSession, *, publisher_id: str = "emic-tests", key_id: str = "test-1") -> tuple[PublisherTrustStore, bytes]:
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
