"""Tests for recomputing stored session totals from their intervals."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from energy_core.config import Settings
from energy_core.db.models import Base, EvChargerModel, EvChargingIntervalModel, EvChargingSessionModel, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.models import EvChargingIntervalModel as IntervalModel
from energy_core.ev_accounting.repair import repair_sessions


@pytest.fixture
async def repair_session(tmp_path):
    db_file = tmp_path / "repair.db"
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


async def _add_zeroed_session(
    session,
    site_id: int,
    charger_id: int,
    *,
    intervals: list[tuple[float, float, float]],
    meter_kwh: float | None = 0.0,
    status: str = "COMPLETED",
) -> int:
    """Store a session the way the old code did: intervals intact, totals zeroed.

    Each interval tuple is (charged_kwh, solar_direct_kwh, grid_direct_kwh).
    """
    started = datetime(2026, 8, 22, 9, 21, tzinfo=UTC)
    row = EvChargingSessionModel(
        charger_id=charger_id,
        site_id=site_id,
        started_at=started,
        ended_at=None if status == "ACTIVE" else started + timedelta(hours=23),
        status=status,
        meter_start_kwh=meter_kwh,
        meter_stop_kwh=meter_kwh,
        total_energy_kwh=0.0,
        solar_direct_kwh=0.0,
        solar_battery_kwh=0.0,
        grid_battery_kwh=0.0,
        grid_direct_kwh=0.0,
        actual_cost_sek=sum(charged * 2.0 for charged, _, _ in intervals),
        savings_baseline="IMMEDIATE_GRID_CHARGING",
        calculation_version="ev-energy-v1",
        reconciliation_delta_kwh=-sum(charged for charged, _, _ in intervals),
    )
    session.add(row)
    await session.flush()
    for index, (charged, solar, grid) in enumerate(intervals):
        session.add(
            EvChargingIntervalModel(
                session_id=row.id,
                charger_id=charger_id,
                start_time=started + timedelta(minutes=index),
                end_time=started + timedelta(minutes=index + 1),
                charged_energy_kwh=charged,
                electricity_price_sek_kwh=2.0,
                solar_direct_kwh=solar,
                solar_battery_kwh=0.0,
                grid_battery_kwh=0.0,
                grid_direct_kwh=grid,
                actual_cost_sek=grid * 2.0,
                reference_cost_sek=charged * 2.0,
                data_quality="MEASURED",
            )
        )
    await session.commit()
    return row.id


@pytest.mark.asyncio
async def test_a_zeroed_session_is_rebuilt_from_its_intervals(repair_session):
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session,
        site_id,
        charger_id,
        intervals=[(1.0, 0.4, 0.6), (1.0, 0.0, 1.0), (1.0, 0.0, 1.0)],
    )

    repairs = await repair_sessions(session, dry_run=False)

    assert len(repairs) == 1
    assert repairs[0].session_id == session_id
    assert repairs[0].old_total_kwh == 0.0
    assert abs(repairs[0].new_total_kwh - 3.0) < 0.01

    row = await session.get(EvChargingSessionModel, session_id)
    assert abs(row.total_energy_kwh - 3.0) < 0.01
    assert abs(row.solar_direct_kwh - 0.4) < 0.01
    assert abs(row.grid_direct_kwh - 2.6) < 0.01
    assert abs(row.renewable_share_pct - 100 * 0.4 / 3.0) < 0.1
    assert row.reconciliation_note == "meter_register_reset"


@pytest.mark.asyncio
async def test_a_dry_run_reports_without_writing(repair_session):
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session, site_id, charger_id, intervals=[(2.0, 1.0, 1.0)]
    )

    repairs = await repair_sessions(session, dry_run=True)

    assert len(repairs) == 1
    row = await session.get(EvChargingSessionModel, session_id)
    assert row.total_energy_kwh == 0.0


@pytest.mark.asyncio
async def test_a_second_run_finds_nothing_left_to_do(repair_session):
    session, site_id, charger_id = repair_session
    await _add_zeroed_session(session, site_id, charger_id, intervals=[(2.0, 1.0, 1.0)])

    await repair_sessions(session, dry_run=False)
    again = await repair_sessions(session, dry_run=False)

    assert again == []


@pytest.mark.asyncio
async def test_a_session_without_intervals_is_left_alone(repair_session):
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(session, site_id, charger_id, intervals=[])

    repairs = await repair_sessions(session, dry_run=False)

    assert repairs == []
    row = await session.get(EvChargingSessionModel, session_id)
    assert row.total_energy_kwh == 0.0


@pytest.mark.asyncio
async def test_a_plausible_meter_total_still_wins(repair_session):
    """A positive meter reading is the billing truth, so it scales the split."""
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session,
        site_id,
        charger_id,
        intervals=[(2.0, 1.0, 1.0), (2.0, 1.0, 1.0)],
        meter_kwh=None,
    )
    row = await session.get(EvChargingSessionModel, session_id)
    row.meter_start_kwh = 100.0
    row.meter_stop_kwh = 102.0
    await session.commit()

    repairs = await repair_sessions(session, dry_run=False)

    assert len(repairs) == 1
    row = await session.get(EvChargingSessionModel, session_id)
    assert abs(row.total_energy_kwh - 2.0) < 0.01
    assert row.reconciliation_note == "scaled_to_meter"


@pytest.mark.asyncio
async def test_a_restart_recount_is_dropped_before_the_total_is_rebuilt(repair_session):
    """Regression: six collector restarts turned 29 kWh into 131 kWh.

    Each restart re-anchored sampling to the session start, so the next sample
    wrote one interval covering everything charged so far.
    """
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session,
        site_id,
        charger_id,
        intervals=[(1.0, 0.0, 1.0)] * 10,
    )
    started = (await session.get(EvChargingSessionModel, session_id)).started_at
    # Two restarts, each re-counting the session from its start.
    for recounted, minutes in ((4.0, 200), (7.0, 300)):
        session.add(
            IntervalModel(
                session_id=session_id,
                charger_id=charger_id,
                start_time=started,
                end_time=started + timedelta(minutes=minutes),
                charged_energy_kwh=recounted,
                electricity_price_sek_kwh=2.0,
                solar_direct_kwh=0.0,
                solar_battery_kwh=0.0,
                grid_battery_kwh=0.0,
                grid_direct_kwh=recounted,
                actual_cost_sek=recounted * 2.0,
                reference_cost_sek=recounted * 2.0,
                data_quality="MEASURED",
            )
        )
    await session.commit()

    repairs = await repair_sessions(session, dry_run=False)

    assert len(repairs) == 1
    assert repairs[0].removed_intervals == 2
    assert abs(repairs[0].removed_kwh - 11.0) < 0.01
    assert abs(repairs[0].new_total_kwh - 10.0) < 0.01
    row = await session.get(EvChargingSessionModel, session_id)
    assert abs(row.total_energy_kwh - 10.0) < 0.01
    remaining = await session.scalars(
        select(IntervalModel).where(IntervalModel.session_id == session_id)
    )
    assert len(list(remaining)) == 10


@pytest.mark.asyncio
async def test_a_dry_run_reports_recounts_without_deleting_them(repair_session):
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session, site_id, charger_id, intervals=[(1.0, 0.0, 1.0)] * 3
    )
    started = (await session.get(EvChargingSessionModel, session_id)).started_at
    session.add(
        IntervalModel(
            session_id=session_id,
            charger_id=charger_id,
            start_time=started,
            end_time=started + timedelta(minutes=120),
            charged_energy_kwh=2.0,
            electricity_price_sek_kwh=2.0,
            solar_direct_kwh=0.0,
            solar_battery_kwh=0.0,
            grid_battery_kwh=0.0,
            grid_direct_kwh=2.0,
            actual_cost_sek=4.0,
            data_quality="MEASURED",
        )
    )
    await session.commit()

    repairs = await repair_sessions(session, dry_run=True)

    assert repairs[0].removed_intervals == 1
    assert abs(repairs[0].new_total_kwh - 3.0) < 0.01
    remaining = await session.scalars(
        select(IntervalModel).where(IntervalModel.session_id == session_id)
    )
    assert len(list(remaining)) == 4


@pytest.mark.asyncio
async def test_a_running_session_is_repaired_without_being_completed(repair_session):
    session, site_id, charger_id = repair_session
    session_id = await _add_zeroed_session(
        session, site_id, charger_id, intervals=[(2.0, 1.0, 1.0)], status="ACTIVE"
    )

    repairs = await repair_sessions(session, dry_run=False)

    assert len(repairs) == 1
    assert repairs[0].status == "ACTIVE"
    row = await session.get(EvChargingSessionModel, session_id)
    assert row.status == "ACTIVE"
    assert abs(row.total_energy_kwh - 2.0) < 0.01


@pytest.mark.asyncio
async def test_another_site_can_be_excluded(repair_session):
    session, site_id, charger_id = repair_session
    await _add_zeroed_session(session, site_id, charger_id, intervals=[(2.0, 1.0, 1.0)])

    assert await repair_sessions(session, site_id=site_id + 99, dry_run=True) == []
    assert len(await repair_sessions(session, site_id=site_id, dry_run=True)) == 1
