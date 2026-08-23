import base64
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from energy_core.config import Settings
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import Base
from energy_core.db.session import create_engine, create_session_factory


def _make_jwt(exp: int) -> str:
    header = base64.urlsafe_b64encode(b"{}").decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.signature"


@pytest.fixture
async def session_factory(tmp_path):
    db_file = tmp_path / "heartbeat-token.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    engine = create_engine(settings)
    factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_ensure_api_token_refreshes_expired_token(session_factory):
    expired = _make_jwt(int(time.time()) - 60)
    async with session_factory() as session:
        repo = HeartbeatSettingsRepository(session)
        row = await repo.get_or_create()
        row.connection_type = "cloud"
        row.username = "user@example.com"
        row.password = "secret"
        row.api_token = expired
        await session.commit()

    with patch(
        "energy_core.db.heartbeat_settings_repo.refresh_bearer_token",
        new=AsyncMock(return_value="fresh-token"),
    ) as refresh:
        async with session_factory() as session:
            repo = HeartbeatSettingsRepository(session)
            token = await repo.ensure_api_token()
            await session.commit()

    assert token == "fresh-token"
    refresh.assert_awaited_once_with("user@example.com", "secret")

    async with session_factory() as session:
        repo = HeartbeatSettingsRepository(session)
        _, stored = await repo.get_secrets()
        assert stored == "fresh-token"


@pytest.mark.asyncio
async def test_ensure_api_token_keeps_valid_token(session_factory):
    valid = _make_jwt(int(time.time()) + 7200)
    async with session_factory() as session:
        repo = HeartbeatSettingsRepository(session)
        row = await repo.get_or_create()
        row.connection_type = "cloud"
        row.username = "user@example.com"
        row.password = "secret"
        row.api_token = valid
        await session.commit()

    with patch(
        "energy_core.db.heartbeat_settings_repo.refresh_bearer_token",
        new=AsyncMock(return_value="should-not-be-used"),
    ) as refresh:
        async with session_factory() as session:
            repo = HeartbeatSettingsRepository(session)
            token = await repo.ensure_api_token()

    assert token == valid
    refresh.assert_not_called()
