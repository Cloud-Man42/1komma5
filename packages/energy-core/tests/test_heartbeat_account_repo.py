import pytest

from energy_core.config import Settings
from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.models import Base, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType


@pytest.fixture
async def session_factory(tmp_path):
    db_file = tmp_path / "heartbeat-account.db"
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
async def test_create_and_list_accounts(session_factory):
    async with session_factory() as session:
        repo = HeartbeatAccountRepository(session)
        record = await repo.create(
            slug="test-account",
            name="Test Account",
            connection_type=HeartbeatConnectionType.CLOUD.value,
            username="user@example.com",
            password="secret",
        )
        await session.commit()

        accounts = await repo.list_accounts()
        assert any(account.slug == "test-account" for account in accounts)
        assert record.password_configured is True


@pytest.mark.asyncio
async def test_resolve_system_id_prefers_heartbeat_system_id():
    repo = HeartbeatAccountRepository(None)  # type: ignore[arg-type]
    site = SiteModel(
        slug="demo",
        name="Demo",
        timezone="UTC",
        external_system_id="legacy-id",
        heartbeat_system_id="new-id",
    )
    assert repo.resolve_system_id(site) == "new-id"


@pytest.mark.asyncio
async def test_resolve_system_id_falls_back_to_external():
    repo = HeartbeatAccountRepository(None)  # type: ignore[arg-type]
    site = SiteModel(slug="demo", name="Demo", timezone="UTC", external_system_id="legacy-id")
    assert repo.resolve_system_id(site) == "legacy-id"
