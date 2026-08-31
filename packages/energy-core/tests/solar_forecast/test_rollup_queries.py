from datetime import UTC, date, datetime

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base, EnergyDailyModel
from energy_core.db.repositories import EnergyReadingRepository, SiteRepository
from energy_core.db.session import create_engine, create_session_factory
from energy_core.solar_forecast.rollup_queries import (
    actual_kwh_for_day_resolved,
    actual_kwh_from_daily,
    actual_solar_kwh_today,
    count_production_days_observed,
    hourly_to_buckets,
    hourly_to_readings,
)


@pytest.fixture
async def sqlite_session():
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
    )
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings
    await engine.dispose()


def test_hourly_to_readings_converts_kwh_to_avg_watts():
    hour = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    from energy_core.db.repositories import HourlyRollup

    readings = hourly_to_readings([HourlyRollup(hour=hour, solar_kwh=2.5, consumption_kwh=1.0)])
    assert readings[0][0] == hour
    assert readings[0][1] == 2500.0
    assert readings[0][2] == 1000.0


def test_hourly_to_buckets_marks_full_hour_coverage():
    hour = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
    from energy_core.db.repositories import HourlyRollup

    buckets = hourly_to_buckets([HourlyRollup(hour=hour, solar_kwh=1.0, consumption_kwh=0.5)])
    assert buckets[0].sample_count == 60
    assert buckets[0].avg_solar_w == 1000.0


def test_actual_kwh_from_daily():
    from energy_core.db.repositories import DailyRollup

    actual, completeness = actual_kwh_from_daily(DailyRollup(day=date(2026, 2, 1), solar_kwh=8.25, consumption_kwh=4.0))
    assert actual == 8.25
    assert completeness == 100.0


@pytest.mark.asyncio
async def test_actual_solar_kwh_today_prefers_daily_rollup(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    session.add(
        EnergyDailyModel(
            site_id=site.id,
            day=datetime.now(UTC).date(),
            solar_kwh=6.7,
            consumption_kwh=4.0,
            import_kwh=0.0,
            export_kwh=2.7,
        )
    )
    await session.commit()

    actual = await actual_solar_kwh_today(
        reading_repo,
        site.id,
        timezone="UTC",
        now=datetime.now(UTC),
    )
    assert actual == 6.7


@pytest.mark.asyncio
async def test_count_production_days_from_daily_rollups(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "UTC")
    session.add_all(
        [
            EnergyDailyModel(
                site_id=site.id,
                day=date(2026, 2, 1),
                solar_kwh=5.0,
                consumption_kwh=3.0,
                import_kwh=0.0,
                export_kwh=2.0,
            ),
            EnergyDailyModel(
                site_id=site.id,
                day=date(2026, 2, 2),
                solar_kwh=0.2,
                consumption_kwh=3.0,
                import_kwh=2.8,
                export_kwh=0.0,
            ),
        ]
    )
    await session.commit()

    count = await count_production_days_observed(
        reading_repo,
        site.id,
        timezone="UTC",
        window_days=7,
        now=datetime(2026, 2, 3, 12, 0, tzinfo=UTC),
    )
    assert count == 1


@pytest.mark.asyncio
async def test_actual_kwh_for_day_resolved_uses_daily(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "UTC")
    session.add(
        EnergyDailyModel(
            site_id=site.id,
            day=date(2026, 2, 1),
            solar_kwh=9.1,
            consumption_kwh=4.0,
            import_kwh=0.0,
            export_kwh=5.1,
        )
    )
    await session.commit()

    actual, completeness = await actual_kwh_for_day_resolved(
        reading_repo,
        site.id,
        date(2026, 2, 1),
        timezone="UTC",
    )
    assert actual == 9.1
    assert completeness == 100.0
