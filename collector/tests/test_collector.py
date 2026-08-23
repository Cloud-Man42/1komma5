from datetime import UTC, datetime

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.normalization import normalize_reading
from energy_core.providers.mock import MockHeartbeatProvider
from energy_core.seed import seed_sites


@pytest.fixture
async def collector_env(tmp_path):
    db_file = tmp_path / "test.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        HEARTBEAT_POLL_INTERVAL=5,
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
    yield session_factory, settings
    await engine.dispose()


@pytest.mark.asyncio
async def test_collector_poll_cycle(collector_env):
    session_factory, settings = collector_env
    provider = MockHeartbeatProvider(seed=99)

    readings = await provider.fetch_readings(datetime(2026, 7, 1, 14, 0, tzinfo=UTC))
    async with session_factory() as session:
        site_repo = SiteRepository(session)
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        for raw in readings:
            normalized = normalize_reading(raw)
            site = await site_repo.get_by_slug(normalized.site_slug)
            assert site is not None
            await reading_repo.upsert_reading(site.id, normalized)
        await session.commit()

    async with session_factory() as session:
        reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
        sites = await SiteRepository(session).list_all()
        for site in sites:
            latest = await reading_repo.get_latest_for_site(site.id)
            assert latest is not None
            assert latest.solar_production_w >= 0
