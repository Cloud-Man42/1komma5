"""Shared fixtures for governance tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.models.module_installation_policy import ModuleInstallationPolicyModel
from energy_core.db.models.module_publisher import ModulePublisherModel
from energy_core.platform.modules.governance.policy_repository import PolicyRepository
from energy_core.platform.modules.governance.types import PublisherStatus, PublisherTier


@pytest.fixture
async def session(tmp_path):
    db_file = tmp_path / "governance.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as db_session:
        yield db_session
    await engine.dispose()


async def seed_publisher(
    session: AsyncSession,
    *,
    publisher_id: str,
    tier: str = PublisherTier.ORG_APPROVED.value,
    status: str = PublisherStatus.ACTIVE.value,
    display_name: str | None = None,
) -> ModulePublisherModel:
    row = ModulePublisherModel(
        publisher_id=publisher_id,
        display_name=display_name or publisher_id,
        tier=tier,
        status=status,
    )
    session.add(row)
    await session.flush()
    return row


async def seed_default_policy(session: AsyncSession) -> ModuleInstallationPolicyModel:
    repo = PolicyRepository(session)
    return await repo.get_or_create()
