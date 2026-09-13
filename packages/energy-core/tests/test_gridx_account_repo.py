"""GridX account token refresh in HeartbeatAccountRepository."""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.config import Settings
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory
from energy_core.integrations.heartbeat.gridx_auth import GridXTokenSet
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider


def _fake_jwt() -> str:
    exp = int(time.time()) + 3600
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@pytest.fixture
async def gridx_repo(tmp_path):
    db_file = tmp_path / "gridx-repo.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="denmark",
            name="Danmark",
            provider=HeartbeatBackendProvider.GRIDX.value,
            username="dk@example.com",
            password="secret",
        )
        await session.commit()
        yield repo, record.id, session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_ensure_api_token_gridx_stores_refresh_token(gridx_repo):
    repo, account_id, session_factory = gridx_repo
    token_set = GridXTokenSet(access_token=_fake_jwt(), refresh_token="refresh-abc")
    with patch(
        "energy_core.db.heartbeat_account_repo.login_gridx_token_set",
        new=AsyncMock(return_value=token_set),
    ):
        async with session_factory() as session:
            repo = HeartbeatAccountRepository(session)
            token = await repo.ensure_api_token(account_id, force=True)
            await session.commit()
    assert token == token_set.access_token
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.get_record(account_id)
        assert record.api_token_configured is True
        assert record.refresh_token_configured is True
        assert record.last_authentication_error is None


@pytest.mark.asyncio
async def test_onekommafive_account_unchanged(gridx_repo):
    repo, _, session_factory = gridx_repo
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="default",
            name="Default",
            provider=HeartbeatBackendProvider.ONEKOMMAFIVE.value,
            username="se@example.com",
            password="secret",
        )
        await session.commit()
        account_id = record.id
    with patch(
        "energy_core.db.heartbeat_account_repo.refresh_bearer_token",
        new=AsyncMock(return_value=_fake_jwt()),
    ):
        async with session_factory() as session:
            repo = HeartbeatAccountRepository(session)
            token = await repo.ensure_api_token(account_id, force=True)
            assert token
