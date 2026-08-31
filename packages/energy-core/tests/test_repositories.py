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
from energy_core.export_revenue.calculator import SellPriceConfig
from energy_core.export_revenue.site_config import sell_price_config_from_site


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
    spot_eur = 1.0 / 11.0
    all_in_eur = 2.5 / 11.0
    await price_repo.upsert_prices(
        site.id,
        [(price_at, spot_eur, all_in_eur)],
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
    market_sek = 2.5
    spot_sek = 1.0
    assert stats[0].solar_savings_sek == pytest.approx(0.167 * market_sek, abs=0.05)
    assert stats[0].battery_savings_sek == pytest.approx(0.042 * market_sek, abs=0.05)
    assert stats[0].export_revenue_sek == pytest.approx(0.017 * spot_sek, abs=0.02)
    assert stats[0].energy_sale_revenue_sek == pytest.approx(0.017 * spot_sek, abs=0.02)
    assert stats[0].grid_import_cost_sek == pytest.approx(0.025 * market_sek, abs=0.05)
    assert stats[0].market_priced_fraction == 1.0
    assert stats[0].export_spot_priced_fraction == 1.0


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


@pytest.mark.asyncio
async def test_financial_stats_does_not_double_count_solar_charged_into_battery(sqlite_session):
    """Solar routed into the battery must not also count as direct solar self-consumption.

    Previously min(solar_w, consumption_w) credited 2000 W of solar even when 500 W was
    charging the battery, and the same energy was credited again later as battery savings.
    """
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    readings = [
        (
            datetime(2026, 8, 18, 10, 0, tzinfo=UTC),
            2000,
            3000,
            1500,
            0,
            500,
        ),
        (
            datetime(2026, 8, 18, 10, 5, tzinfo=UTC),
            0,
            500,
            0,
            0,
            -500,
        ),
        (
            datetime(2026, 8, 18, 10, 10, tzinfo=UTC),
            0,
            500,
            0,
            0,
            0,
        ),
    ]
    for recorded_at, solar, consumption, grid_import, grid_export, battery_power in readings:
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=recorded_at,
                solar_production_w=solar,
                consumption_w=consumption,
                grid_import_w=grid_import,
                grid_export_w=grid_export,
                battery_soc_pct=50,
                battery_power_w=battery_power,
            ),
        )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
    )

    assert len(stats) == 1
    # Old buggy attribution would have been solar=0.167, battery=0.042, import=0.125 (sum 0.334 kWh).
    assert stats[0].solar_self_consumed_kwh == pytest.approx(0.125, abs=0.001)
    assert stats[0].battery_self_consumed_kwh == pytest.approx(0.042, abs=0.001)
    assert stats[0].imported_kwh == pytest.approx(0.125, abs=0.001)
    attributed_kwh = (
        stats[0].solar_self_consumed_kwh
        + stats[0].battery_self_consumed_kwh
        + stats[0].imported_kwh
    )
    measured_consumption_kwh = (3000 + 500) * (5 / 60) / 1000
    assert attributed_kwh == pytest.approx(measured_consumption_kwh, abs=0.001)


@pytest.mark.asyncio
async def test_financial_stats_grid_charged_battery_keeps_balanced_result(sqlite_session):
    """Grid-charged battery discharge is a cost at import and savings at discharge."""
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    readings = [
        (
            datetime(2026, 8, 18, 22, 0, tzinfo=UTC),
            0,
            0,
            1000,
            0,
            1000,
        ),
        (
            datetime(2026, 8, 18, 22, 5, tzinfo=UTC),
            0,
            1000,
            0,
            0,
            -1000,
        ),
        (
            datetime(2026, 8, 18, 22, 10, tzinfo=UTC),
            0,
            0,
            0,
            0,
            0,
        ),
    ]
    for recorded_at, solar, consumption, grid_import, grid_export, battery_power in readings:
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=recorded_at,
                solar_production_w=solar,
                consumption_w=consumption,
                grid_import_w=grid_import,
                grid_export_w=grid_export,
                battery_soc_pct=50,
                battery_power_w=battery_power,
            ),
        )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
    )

    assert len(stats) == 1
    assert stats[0].solar_self_consumed_kwh == pytest.approx(0.0, abs=0.001)
    assert stats[0].battery_self_consumed_kwh == pytest.approx(0.083, abs=0.001)
    assert stats[0].imported_kwh == pytest.approx(0.083, abs=0.001)
    assert stats[0].battery_savings_sek == pytest.approx(0.17, abs=0.01)
    assert stats[0].grid_import_cost_sek == pytest.approx(0.17, abs=0.01)
    net = (
        stats[0].solar_savings_sek
        + stats[0].battery_savings_sek
        + stats[0].export_revenue_sek
        - stats[0].grid_import_cost_sek
    )
    assert net == pytest.approx(0.0, abs=0.01)


@pytest.mark.asyncio
async def test_get_latest_for_sites_returns_one_reading_per_site(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    akarp = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    other = await site_repo.upsert_site("other", "Other", "Europe/Stockholm")

    for site, solar, ts in (
        (akarp, 1000.0, datetime(2026, 2, 1, 10, 0, tzinfo=UTC)),
        (akarp, 2000.0, datetime(2026, 2, 1, 11, 0, tzinfo=UTC)),
        (other, 3000.0, datetime(2026, 2, 1, 9, 0, tzinfo=UTC)),
    ):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug=site.slug,
                recorded_at=ts,
                solar_production_w=solar,
                consumption_w=500,
                grid_import_w=0,
                grid_export_w=0,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    await session.commit()

    latest = await reading_repo.get_latest_for_sites([akarp.id, other.id, 9999])
    assert latest[akarp.id].solar_production_w == 2000.0
    assert latest[other.id].solar_production_w == 3000.0
    assert 9999 not in latest


@pytest.mark.asyncio
async def test_list_sites_with_latest_uses_single_batch_query(sqlite_session):
    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    akarp = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    await site_repo.upsert_site("empty", "Empty", "Europe/Stockholm")
    await reading_repo.upsert_reading(
        akarp.id,
        NormalizedEnergyReading(
            site_slug="akarp",
            recorded_at=datetime(2026, 2, 1, 12, 0, tzinfo=UTC),
            solar_production_w=1500,
            consumption_w=500,
            grid_import_w=0,
            grid_export_w=0,
            battery_soc_pct=50,
            battery_power_w=0,
        ),
    )
    await session.commit()

    sites = await reading_repo.list_sites_with_latest()
    by_slug = {site.slug: site for site in sites}
    assert by_slug["akarp"].latest_reading is not None
    assert by_slug["akarp"].latest_reading.solar_production_w == 1500
    assert by_slug["empty"].latest_reading is None


@pytest.mark.asyncio
async def test_daily_and_hourly_rollups_round_trip(sqlite_session):
    from datetime import date

    from energy_core.db.models import EnergyDailyModel, EnergyHourlyModel

    session, settings = sqlite_session
    site_repo = SiteRepository(session)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    site = await site_repo.upsert_site("akarp", "Åkarp", "Europe/Stockholm")
    session.add(
        EnergyHourlyModel(
            site_id=site.id,
            hour=datetime(2026, 2, 1, 10, 0, tzinfo=UTC),
            solar_kwh=1.5,
            consumption_kwh=0.8,
            import_kwh=0.0,
            export_kwh=0.7,
        )
    )
    session.add(
        EnergyDailyModel(
            site_id=site.id,
            day=date(2026, 2, 1),
            solar_kwh=12.3,
            consumption_kwh=9.8,
            import_kwh=1.0,
            export_kwh=3.5,
        )
    )
    await session.commit()

    hourly = await reading_repo.list_hourly_rollups(site.id)
    daily = await reading_repo.list_daily_rollups(site.id)
    assert hourly[0].solar_kwh == 1.5
    assert daily[0].solar_kwh == 12.3
    assert (await reading_repo.get_daily_rollup(site.id, date(2026, 2, 1))).solar_kwh == 12.3


@pytest.mark.asyncio
async def test_financial_stats_export_uses_spot_not_flat_rate(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 13, minute, tzinfo=UTC),
                solar_production_w=3000,
                consumption_w=1000,
                grid_import_w=0,
                grid_export_w=2400,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    await price_repo.upsert_prices(site.id, [(datetime(2026, 8, 18, 13, tzinfo=UTC), 0.72 / 11.0, 1.0)])
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(fallback_flat_price_sek_kwh=0.8),
    )

    export_kwh = stats[0].exported_kwh
    assert export_kwh == pytest.approx(0.2, abs=0.02)
    assert stats[0].energy_sale_revenue_sek == pytest.approx(export_kwh * 0.72, abs=0.02)
    assert stats[0].export_revenue_sek != pytest.approx(export_kwh * 0.8, abs=0.001)


@pytest.mark.asyncio
async def test_financial_stats_negative_spot_export_revenue(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 3, minute, tzinfo=UTC),
                solar_production_w=0,
                consumption_w=0,
                grid_import_w=0,
                grid_export_w=2000,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    await price_repo.upsert_prices(site.id, [(datetime(2026, 8, 18, 3, tzinfo=UTC), -0.20 / 11.0, 0.5)])
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(),
    )

    export_kwh = stats[0].exported_kwh
    assert stats[0].energy_sale_revenue_sek == pytest.approx(export_kwh * -0.20, abs=0.02)
    assert stats[0].energy_sale_revenue_sek < 0


@pytest.mark.asyncio
async def test_financial_stats_tax_credit_zero_in_2026(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 1, 1, 10, minute, tzinfo=UTC),
                solar_production_w=2000,
                consumption_w=0,
                grid_import_w=1000,
                grid_export_w=1000,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=sell_price_config_from_site(site),
    )

    assert stats[0].tax_credit_sek == 0.0


@pytest.mark.asyncio
async def test_financial_stats_tax_credit_2025_with_limits(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2025, 6, 15, 10, minute, tzinfo=UTC),
                solar_production_w=5000,
                consumption_w=0,
                grid_import_w=500,
                grid_export_w=5000,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=sell_price_config_from_site(site),
    )

    export_kwh = stats[0].exported_kwh
    eligible = min(export_kwh, stats[0].imported_kwh)
    assert stats[0].tax_credit_sek == pytest.approx(eligible * 0.60, abs=0.05)


@pytest.mark.asyncio
async def test_financial_stats_export_uses_feed_in_tariff_not_spot(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 13, minute, tzinfo=UTC),
                solar_production_w=3000,
                consumption_w=1000,
                grid_import_w=0,
                grid_export_w=2400,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    price_at = datetime(2026, 8, 18, 13, tzinfo=UTC)
    feed_in_eur = 0.075
    spot_eur = 0.72 / 11.0
    await price_repo.upsert_prices(site.id, [(price_at, spot_eur, 1.0 / 11.0, feed_in_eur)])
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(pricing_mode="feed_in", fallback_flat_price_sek_kwh=0.8),
    )

    export_kwh = stats[0].exported_kwh
    feed_in_sek = 0.075 * 11.0
    assert stats[0].energy_sale_revenue_sek == pytest.approx(export_kwh * feed_in_sek, abs=0.02)
    assert stats[0].energy_sale_revenue_sek != pytest.approx(export_kwh * 0.72, abs=0.02)


@pytest.mark.asyncio
async def test_financial_stats_legacy_sek_spot_not_doubled(sqlite_session):
    """Pre-migration rows stored as SEK/kWh must not be multiplied by EUR rate again."""
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 14, minute, tzinfo=UTC),
                solar_production_w=2000,
                consumption_w=0,
                grid_import_w=0,
                grid_export_w=2000,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    await price_repo.upsert_prices(
        site.id,
        [(datetime(2026, 8, 18, 14, tzinfo=UTC), 0.72, 2.5, None)],
    )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(pricing_mode="spot"),
    )

    export_kwh = stats[0].exported_kwh
    assert stats[0].energy_sale_revenue_sek == pytest.approx(export_kwh * 0.72, abs=0.02)
    assert stats[0].solar_savings_sek == pytest.approx(0.0, abs=0.01)


@pytest.mark.asyncio
async def test_market_price_backfill_missing_feed_in(sqlite_session):
    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    hours = [
        datetime(2026, 8, 18, 10, tzinfo=UTC),
        datetime(2026, 8, 18, 11, tzinfo=UTC),
    ]
    await price_repo.upsert_prices(
        site.id,
        [(hour, 0.08, 0.2, None) for hour in hours],
    )
    updated = await price_repo.backfill_missing_feed_in(site.id, 0.075)
    await session.commit()
    assert updated == 2
    record = await price_repo.get_at(site.id, hours[0])
    assert record is not None
    assert record.feed_in_price_eur_kwh == pytest.approx(0.075)


@pytest.mark.asyncio
async def test_financial_stats_export_zero_before_contract_start(sqlite_session):
    from datetime import date

    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    site.sell_contract_start_date = date(2026, 8, 25)
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 18, 13, minute, tzinfo=UTC),
                solar_production_w=3000,
                consumption_w=1000,
                grid_import_w=0,
                grid_export_w=2400,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    await price_repo.upsert_prices(
        site.id,
        [(datetime(2026, 8, 18, 13, tzinfo=UTC), 0.72 / 11.0, 1.0 / 11.0, 0.075)],
    )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(
            pricing_mode="feed_in",
            fallback_flat_price_sek_kwh=0.8,
            sell_contract_start_date=date(2026, 8, 25),
        ),
    )

    assert stats[0].exported_kwh == pytest.approx(0.2, abs=0.02)
    assert stats[0].uncontracted_exported_kwh == pytest.approx(0.2, abs=0.02)
    assert stats[0].export_revenue_sek == 0.0
    assert stats[0].energy_sale_revenue_sek == 0.0


@pytest.mark.asyncio
async def test_financial_stats_export_counts_from_contract_start_day(sqlite_session):
    from datetime import date

    session, settings = sqlite_session
    site = await SiteRepository(session).upsert_site("akarp", "Åkarp", "UTC")
    reading_repo = EnergyReadingRepository(session, is_sqlite=settings.is_sqlite)
    for minute in (0, 5):
        await reading_repo.upsert_reading(
            site.id,
            NormalizedEnergyReading(
                site_slug="akarp",
                recorded_at=datetime(2026, 8, 25, 13, minute, tzinfo=UTC),
                solar_production_w=3000,
                consumption_w=1000,
                grid_import_w=0,
                grid_export_w=2400,
                battery_soc_pct=50,
                battery_power_w=0,
            ),
        )
    price_repo = MarketPriceRepository(session, is_sqlite=True)
    await price_repo.upsert_prices(
        site.id,
        [(datetime(2026, 8, 25, 13, tzinfo=UTC), 0.72 / 11.0, 1.0 / 11.0, 0.075)],
    )
    await session.commit()

    stats = await reading_repo.list_financial_stats(
        site.id,
        "day",
        "UTC",
        fallback_purchase_price_sek_kwh=2.0,
        export_compensation_sek_kwh=0.8,
        sell_config=SellPriceConfig(
            pricing_mode="feed_in",
            fallback_flat_price_sek_kwh=0.8,
            sell_contract_start_date=date(2026, 8, 25),
        ),
    )

    export_kwh = stats[0].exported_kwh
    assert stats[0].uncontracted_exported_kwh == pytest.approx(0.0, abs=0.001)
    assert stats[0].export_revenue_sek == pytest.approx(export_kwh * 0.075 * 11.0, abs=0.02)
