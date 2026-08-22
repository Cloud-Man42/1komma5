from datetime import UTC, datetime

import pytest
from energy_core.config import Settings
from energy_core.db.models import Base
from energy_core.db.repositories import (
    EnergyReadingRepository,
    MarketPriceRepository,
    SiteRepository,
)
from energy_core.db.session import create_engine, create_session_factory
from energy_core.domain import NormalizedEnergyReading


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


@pytest.mark.asyncio
async def test_site_and_reading_upsert(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)

    site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    await session.commit()

    reading = NormalizedEnergyReading(
        site_slug="akarp",
        recorded_at=datetime.now(UTC),
        solar_production_w=1000,
        consumption_w=500,
        grid_import_w=0,
        grid_export_w=500,
        battery_soc_pct=80,
        battery_power_w=100,
    )
    await reading_repo.upsert_reading(site.id, reading)
    await session.commit()

    latest = await reading_repo.get_latest_for_site(site.id)
    assert latest is not None
    assert latest.solar_production_w == 1000


@pytest.mark.asyncio
async def test_reading_upsert_idempotent(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    for solar in (1000.0, 2000.0):
        reading = NormalizedEnergyReading(
            site_slug="akarp",
            recorded_at=ts,
            solar_production_w=solar,
            consumption_w=500,
            grid_import_w=0,
            grid_export_w=0,
            battery_soc_pct=50,
            battery_power_w=0,
        )
        await reading_repo.upsert_reading(site.id, reading)
    await session.commit()

    latest = await reading_repo.get_latest_for_site(site.id)
    assert latest is not None
    assert latest.solar_production_w == 2000.0


@pytest.mark.asyncio
async def test_list_peaks_separates_battery_charge_and_discharge(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")

    values = [
        (datetime(2026, 1, 31, 23, 30, tzinfo=UTC), 1200, 800),
        (datetime(2026, 2, 1, 10, 0, tzinfo=UTC), 7800, -2500),
        (datetime(2026, 2, 1, 11, 0, tzinfo=UTC), 6500, 3200),
    ]
    for recorded_at, solar, battery in values:
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=recorded_at,
                solar_production_w=solar,
                consumption_w=500,
                grid_import_w=0,
                grid_export_w=0,
                battery_soc_pct=50,
                battery_power_w=battery,
            ),
        )
    await session.commit()

    daily = await reading_repo.list_peaks(site.id, "day", "Europe/Stockholm")

    assert len(daily) == 1
    assert daily[0].period_start == "2026-02-01"
    assert daily[0].solar_production_w == 7800
    assert daily[0].battery_charge_w == 3200
    assert daily[0].battery_discharge_w == 2500


@pytest.mark.asyncio
async def test_list_peaks_returns_zero_when_battery_only_moves_one_direction(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "UTC")
    await reading_repo.upsert_reading(
        site.id,
        NormalizedEnergyReading(
            site_slug="akarp",
            recorded_at=datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
            solar_production_w=1000,
            consumption_w=500,
            grid_import_w=0,
            grid_export_w=0,
            battery_soc_pct=50,
            battery_power_w=-1800,
        ),
    )
    await session.commit()

    monthly = await reading_repo.list_peaks(site.id, "month", "UTC")

    assert monthly[0].battery_charge_w == 0
    assert monthly[0].battery_discharge_w == 1800


@pytest.mark.asyncio
async def test_financial_stats_values_solar_battery_and_export_with_market_price(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 10, minute, tzinfo=UTC),
                solar_production_w=2000,
                consumption_w=3000,
                grid_import_w=300,
                grid_export_w=200,
                battery_soc_pct=50,
                battery_power_w=-500,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    price_at = datetime(2026, 8, 18, 10, tzinfo=UTC)
    await price_repo.upsert_prices(
        site.id,
        [(price_at, 1.0, 2.5)],
    )
    await session.commit()
    assert await price_repo.has_price_at(site.id, price_at)

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
    )

    assert len(stats) == 1
    assert stats[0].solar_self_consumed_kwh == pytest.approx(0.167, abs=0.001)
    assert stats[0].battery_self_consumed_kwh == pytest.approx(0.042, abs=0.001)
    assert stats[0].exported_kwh == pytest.approx(0.017, abs=0.001)
    assert stats[0].imported_kwh == pytest.approx(0.025, abs=0.001)
    assert stats[0].solar_savings_sek == 0.42
    assert stats[0].battery_savings_sek == 0.1
    assert stats[0].export_revenue_sek == 0.01
    assert stats[0].grid_import_cost_sek == 0.06
    assert stats[0].market_priced_fraction == 1.0


@pytest.mark.asyncio
async def test_financial_stats_uses_fallback_and_ignores_long_data_gaps(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5, 20):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 10, minute, tzinfo=UTC),
                solar_production_w=1000,
                consumption_w=1000,
                grid_import_w=0,
                grid_export_w=0,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=3.0,
        export_compensation_sek_kwh=1.0,
    )

    assert stats[0].solar_self_consumed_kwh == pytest.approx(0.083, abs=0.001)
    assert stats[0].solar_savings_sek == 0.25
    assert stats[0].market_priced_fraction == 0.0
