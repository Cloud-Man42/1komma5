"""Tests for EV charging statistics over periods."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.config import Settings
from energy_core.db.ev_session_repo import EvChargingSessionRepository
from energy_core.db.models import Base, EvChargerModel, EvChargingSessionModel, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.ev_accounting.statistics import EVStatisticsService


@pytest.fixture
async def stats_session(tmp_path):
    db_file = tmp_path / "stats.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        charger = EvChargerModel(
            site_id=site.id,
            name="Halo",
            manufacturer="ChargeAmps",
            model="Halo",
            control_source="chargeamp",
        )
        session.add(charger)
        await session.flush()
        yield session, site.id, charger.id
    await engine.dispose()


async def _add_session(
    session,
    site_id: int,
    charger_id: int,
    *,
    status: str,
    hours_ago: float,
    energy_kwh: float,
    solar_direct_kwh: float = 0.0,
    grid_direct_kwh: float | None = None,
) -> int:
    started = datetime.now(UTC) - timedelta(hours=hours_ago)
    row = EvChargingSessionModel(
        charger_id=charger_id,
        site_id=site_id,
        started_at=started,
        ended_at=None if status == "ACTIVE" else started + timedelta(hours=1),
        status=status,
        total_energy_kwh=energy_kwh,
        solar_direct_kwh=solar_direct_kwh,
        solar_battery_kwh=0.0,
        grid_battery_kwh=0.0,
        grid_direct_kwh=energy_kwh - solar_direct_kwh if grid_direct_kwh is None else grid_direct_kwh,
        actual_cost_sek=energy_kwh * 2.0,
        savings_baseline="IMMEDIATE_GRID_CHARGING",
        calculation_version="ev-energy-v1",
    )
    session.add(row)
    await session.commit()
    return row.id


@pytest.mark.asyncio
async def test_a_day_stats_include_the_session_still_charging(stats_session):
    """Regression: a day of charging read 0 kWh until the car was unplugged."""
    session, site_id, charger_id = stats_session
    await _add_session(
        session, site_id, charger_id, status="ACTIVE", hours_ago=4, energy_kwh=101.6, solar_direct_kwh=0.02
    )

    service = EVStatisticsService(EvChargingSessionRepository(session))
    stats = await service.stats(charger_id, period="day")

    assert abs(stats.total_energy_kwh - 101.6) < 0.01
    assert stats.session_count == 1
    assert abs(stats.grid_direct_kwh - 101.58) < 0.01
    assert stats.grid_share_percent > 99


@pytest.mark.asyncio
async def test_a_completed_and_active_sessions_add_up(stats_session):
    session, site_id, charger_id = stats_session
    await _add_session(
        session, site_id, charger_id, status="COMPLETED", hours_ago=10, energy_kwh=4.0, solar_direct_kwh=4.0
    )
    await _add_session(session, site_id, charger_id, status="ACTIVE", hours_ago=2, energy_kwh=6.0)

    service = EVStatisticsService(EvChargingSessionRepository(session))
    stats = await service.stats(charger_id, period="day")

    assert abs(stats.total_energy_kwh - 10.0) < 0.01
    assert stats.session_count == 2
    assert abs(stats.solar_direct_kwh - 4.0) < 0.01
    assert abs(stats.renewable_share_percent - 40.0) < 0.1


@pytest.mark.asyncio
async def test_a_session_outside_the_window_is_excluded(stats_session):
    session, site_id, charger_id = stats_session
    await _add_session(
        session, site_id, charger_id, status="COMPLETED", hours_ago=40, energy_kwh=50.0
    )

    service = EVStatisticsService(EvChargingSessionRepository(session))
    day = await service.stats(charger_id, period="day")
    week = await service.stats(charger_id, period="week")

    assert day.total_energy_kwh == 0.0
    assert day.session_count == 0
    assert abs(week.total_energy_kwh - 50.0) < 0.01


@pytest.mark.asyncio
async def test_an_empty_period_reports_zero_without_dividing_by_it(stats_session):
    session, _site_id, charger_id = stats_session

    service = EVStatisticsService(EvChargingSessionRepository(session))
    stats = await service.stats(charger_id, period="day")

    assert stats.total_energy_kwh == 0.0
    assert stats.average_cost_sek_per_kwh is None
    assert stats.renewable_share_percent == 0.0
    assert stats.grid_share_percent == 0.0
