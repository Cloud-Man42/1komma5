"""Per-account Heartbeat client factory fault isolation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.config import Settings
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.client_factory import create_heartbeat_clients_by_account
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType


@pytest.mark.asyncio
async def test_bad_account_auth_does_not_block_other_clients(tmp_path):
    db_file = tmp_path / "factory-isolation.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        bad = await repo.create(
            slug="denmark",
            name="Danmark Heartbeat Account",
            connection_type=HeartbeatConnectionType.CLOUD.value,
            username="bad@example.com",
            password="wrong",
        )
        good = await repo.create(
            slug="default",
            name="Default Heartbeat Account",
            connection_type=HeartbeatConnectionType.CLOUD.value,
            username="good@example.com",
            password="secret",
        )
        await session.commit()
        bad_id, good_id = bad.id, good.id

    async def fake_client_for_account(session, account_repo, account_id):
        if account_id == bad_id:
            raise HeartbeatAuthError("login failed")
        return object()

    with patch(
        "energy_core.integrations.heartbeat.client_factory._client_for_account",
        new=AsyncMock(side_effect=fake_client_for_account),
    ):
        async with session_factory() as session:
            clients = await create_heartbeat_clients_by_account(session)

    assert bad_id not in clients
    assert good_id in clients
    await engine.dispose()
