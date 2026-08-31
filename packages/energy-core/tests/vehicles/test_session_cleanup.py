"""Tests for purging vehicle charge history that records nothing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from energy_core.config import Settings
from energy_core.db.models import (
    Base,
    EvChargerModel,
    SiteModel,
    VehicleChargeSessionModel,
    VehicleChargingIntervalModel,
    VehicleModel,
    VehicleStateHistoryModel,
)
from energy_core.db.session import create_engine, create_session_factory
from energy_core.vehicles.sessions.cleanup import (
    count_empty_state_rows,
    find_empty_sessions,
    purge_empty_history,
)

CONNECTED = datetime(2026, 8, 23, 18, 27, tzinfo=UTC)


@pytest.fixture
async def cleanup_session(tmp_path):
    db_file = tmp_path / "cleanup.db"
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
        vehicle = VehicleModel(site_id=site.id, provider="mercedes", external_id="eqe", model="EQE")
        session.add_all([charger, vehicle])
        await session.commit()
        yield session_factory, site.id, vehicle.id, charger.id
    await engine.dispose()


def _session_row(site_id: int, vehicle_id: int, charger_id: int, **overrides) -> VehicleChargeSessionModel:
    fields = {
        "site_id": site_id,
        "vehicle_id": vehicle_id,
        "charger_id": charger_id,
        "connected_at": CONNECTED,
        "disconnected_at": CONNECTED + timedelta(minutes=8),
        "status": "COMPLETED",
        "start_soc": 100.0,
    }
    fields.update(overrides)
    return VehicleChargeSessionModel(**fields)


async def _session_count(session_factory) -> int:
    async with session_factory() as session:
        total = await session.execute(select(func.count()).select_from(VehicleChargeSessionModel))
        return total.scalar_one()


@pytest.mark.asyncio
async def test_a_plug_in_that_never_charged_is_removed(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(_session_row(site_id, vehicle_id, charger_id))
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert len(result.sessions) == 1
    assert await _session_count(session_factory) == 0


@pytest.mark.asyncio
async def test_a_session_that_charged_is_kept(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(_session_row(site_id, vehicle_id, charger_id, halo_energy_kwh=12.4))
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.sessions == ()
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_a_session_with_an_estimated_delta_is_kept(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(
            _session_row(site_id, vehicle_id, charger_id, estimated_battery_energy_delta_kwh=3.1)
        )
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.sessions == ()
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_a_session_with_intervals_is_kept(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        row = _session_row(site_id, vehicle_id, charger_id)
        session.add(row)
        await session.flush()
        session.add(
            VehicleChargingIntervalModel(
                session_id=row.id,
                vehicle_id=vehicle_id,
                charger_id=charger_id,
                start_time=CONNECTED,
                end_time=CONNECTED + timedelta(minutes=5),
                charged_energy_kwh=0.0,
            )
        )
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.sessions == ()
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_a_session_that_started_charging_is_kept(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(_session_row(site_id, vehicle_id, charger_id, charging_started_at=CONNECTED))
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.sessions == ()
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_the_running_session_is_left_alone_even_when_empty(cleanup_session):
    """The car may be plugged in right now and about to charge into it."""
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(
            _session_row(site_id, vehicle_id, charger_id, status="ACTIVE", disconnected_at=None)
        )
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.sessions == ()
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_a_dry_run_reports_without_deleting(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(_session_row(site_id, vehicle_id, charger_id))
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=True)
        await session.commit()

    assert len(result.sessions) == 1
    assert await _session_count(session_factory) == 1


@pytest.mark.asyncio
async def test_another_site_is_not_touched_when_scoped(cleanup_session):
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        session.add(_session_row(site_id, vehicle_id, charger_id))
        await session.commit()

    async with session_factory() as session:
        found = await find_empty_sessions(session, site_id=site_id + 99)
        assert found == ()


@pytest.mark.asyncio
async def test_state_rows_without_telemetry_are_removed(cleanup_session):
    session_factory, _site_id, vehicle_id, _charger_id = cleanup_session
    async with session_factory() as session:
        session.add_all(
            [
                VehicleStateHistoryModel(
                    vehicle_id=vehicle_id,
                    recorded_at=CONNECTED,
                    connection_state="CONNECTED",
                    data_quality="UNKNOWN",
                ),
                VehicleStateHistoryModel(
                    vehicle_id=vehicle_id,
                    recorded_at=CONNECTED + timedelta(minutes=1),
                    state_of_charge_percent=100.0,
                    connection_state="CONNECTED",
                    data_quality="MEASURED",
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        assert await count_empty_state_rows(session) == 1
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert result.state_rows == 1
    async with session_factory() as session:
        remaining = await session.scalars(select(VehicleStateHistoryModel))
        rows = list(remaining)
        assert len(rows) == 1
        assert rows[0].state_of_charge_percent == 100.0


@pytest.mark.asyncio
async def test_state_rows_can_be_kept(cleanup_session):
    session_factory, _site_id, vehicle_id, _charger_id = cleanup_session
    async with session_factory() as session:
        session.add(
            VehicleStateHistoryModel(
                vehicle_id=vehicle_id,
                recorded_at=CONNECTED,
                connection_state="CONNECTED",
                data_quality="UNKNOWN",
            )
        )
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, include_state_rows=False, dry_run=False)
        await session.commit()

    assert result.state_rows == 0
    async with session_factory() as session:
        total = await session.execute(select(func.count()).select_from(VehicleStateHistoryModel))
        assert total.scalar_one() == 1


@pytest.mark.asyncio
async def test_nothing_to_purge_reports_an_empty_result(cleanup_session):
    session_factory, _site_id, _vehicle_id, _charger_id = cleanup_session
    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()
    assert result.total == 0


@pytest.mark.asyncio
async def test_the_intervals_of_a_purged_session_go_with_it(cleanup_session):
    """A stray interval on an otherwise empty session must not outlive it."""
    session_factory, site_id, vehicle_id, charger_id = cleanup_session
    async with session_factory() as session:
        empty = _session_row(site_id, vehicle_id, charger_id)
        charged = _session_row(site_id, vehicle_id, charger_id, halo_energy_kwh=5.0)
        session.add_all([empty, charged])
        await session.flush()
        session.add(
            VehicleChargingIntervalModel(
                session_id=charged.id,
                vehicle_id=vehicle_id,
                charger_id=charger_id,
                start_time=CONNECTED,
                end_time=CONNECTED + timedelta(minutes=5),
                charged_energy_kwh=5.0,
            )
        )
        await session.commit()

    async with session_factory() as session:
        result = await purge_empty_history(session, dry_run=False)
        await session.commit()

    assert len(result.sessions) == 1
    async with session_factory() as session:
        intervals = await session.execute(select(func.count()).select_from(VehicleChargingIntervalModel))
        assert intervals.scalar_one() == 1
        assert await _session_count(session_factory) == 1
