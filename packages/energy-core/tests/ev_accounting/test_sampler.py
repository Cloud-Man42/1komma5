"""Tests for interval sampling keeping a running session up to date."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.chargers.meter_adapter import MeterSnapshot
from energy_core.config import Settings
from energy_core.db.ev_session_repo import EvChargingSessionRepository
from energy_core.db.models import Base, EvChargerModel, EvChargingSessionModel, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.ev_accounting.sampler import EVSessionSampler
from energy_core.ev_accounting.session_service import EVSessionService

STARTED = datetime(2026, 8, 30, 8, 57, tzinfo=UTC)


@pytest.fixture
async def sampler_session(tmp_path):
    db_file = tmp_path / "sampler.db"
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
        active = EvChargingSessionModel(
            charger_id=charger.id,
            site_id=site.id,
            started_at=STARTED,
            status="ACTIVE",
            meter_start_kwh=100.0,
            savings_baseline="IMMEDIATE_GRID_CHARGING",
            calculation_version="ev-energy-v1",
        )
        session.add(active)
        await session.commit()
        yield session, site, charger, active.id
    await engine.dispose()


def _meter(cumulative_kwh: float, *, minutes: int) -> MeterSnapshot:
    return MeterSnapshot(
        recorded_at=STARTED + timedelta(minutes=minutes),
        cumulative_kwh=cumulative_kwh,
        power_w=13_700.0,
        configured_current_a=16.0,
        actual_charging_current_a=16.0,
        is_charging=True,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=16.0,
        phase_current_l2_a=16.0,
        phase_current_l3_a=16.0,
        energy_source="meter",
    )


def _grid_sample() -> SiteEnergySample:
    """Night-time import: no sun, no battery, everything off the grid."""
    return SiteEnergySample(
        pv_power_w=0.0,
        house_consumption_w=0.0,
        grid_import_w=14_000.0,
        grid_export_w=0.0,
        battery_charge_w=0.0,
        battery_discharge_w=0.0,
        ev_power_w=13_700.0,
        electricity_price_sek_kwh=2.0,
        duration_hours=1.0,
    )


@pytest.mark.asyncio
async def test_a_running_session_carries_its_energy_before_it_ends(sampler_session):
    """Regression: an ACTIVE session held no totals, so today's stats read 0."""
    session, site, charger, session_id = sampler_session
    service = EVSessionService()
    runtime = service.get_runtime_state(charger.id)
    runtime.last_meter_kwh = 100.0
    runtime.last_sample_at = STARTED
    sampler = EVSessionSampler(service)

    await sampler.sample_active_session(
        session,
        charger=charger,
        site=site,
        meter=_meter(102.0, minutes=1),
        energy_sample=_grid_sample(),
        is_sqlite=True,
    )

    row = await session.get(EvChargingSessionModel, session_id)
    assert row.status == "ACTIVE"
    assert abs(row.total_energy_kwh - 2.0) < 0.01
    assert abs(row.grid_direct_kwh - 2.0) < 0.01
    assert row.actual_cost_sek is not None and row.actual_cost_sek > 0
    assert row.grid_share_pct > 99
    # The meter total is not final while charging, so the energy is an estimate.
    assert row.energy_quality == "ESTIMATED"


@pytest.mark.asyncio
async def test_a_running_total_grows_with_each_sample(sampler_session):
    session, site, charger, session_id = sampler_session
    service = EVSessionService()
    runtime = service.get_runtime_state(charger.id)
    runtime.last_meter_kwh = 100.0
    runtime.last_sample_at = STARTED
    sampler = EVSessionSampler(service)

    for cumulative, minutes in ((102.0, 1), (105.0, 2), (105.5, 3)):
        await sampler.sample_active_session(
            session,
            charger=charger,
            site=site,
            meter=_meter(cumulative, minutes=minutes),
            energy_sample=_grid_sample(),
            is_sqlite=True,
        )

    row = await session.get(EvChargingSessionModel, session_id)
    assert abs(row.total_energy_kwh - 5.5) < 0.01
    assert row.status == "ACTIVE"


@pytest.mark.asyncio
async def test_a_sample_without_energy_leaves_the_totals_untouched(sampler_session):
    """Plugged in but idle must not invent energy or a source split."""
    session, site, charger, session_id = sampler_session
    service = EVSessionService()
    runtime = service.get_runtime_state(charger.id)
    runtime.last_meter_kwh = 100.0
    runtime.last_sample_at = STARTED
    sampler = EVSessionSampler(service)

    idle_meter = MeterSnapshot(
        recorded_at=STARTED + timedelta(minutes=1),
        cumulative_kwh=100.0,
        power_w=0.0,
        configured_current_a=16.0,
        actual_charging_current_a=0.0,
        is_charging=False,
        vehicle_connected=True,
        ocpp_status="SuspendedEV",
        phase_current_l1_a=0.0,
        phase_current_l2_a=0.0,
        phase_current_l3_a=0.0,
        energy_source="meter",
    )
    idle_sample = SiteEnergySample(
        pv_power_w=0.0,
        house_consumption_w=0.0,
        grid_import_w=0.0,
        grid_export_w=0.0,
        battery_charge_w=0.0,
        battery_discharge_w=0.0,
        ev_power_w=0.0,
        electricity_price_sek_kwh=2.0,
        duration_hours=1.0,
    )

    await sampler.sample_active_session(
        session,
        charger=charger,
        site=site,
        meter=idle_meter,
        energy_sample=idle_sample,
        is_sqlite=True,
    )

    row = await session.get(EvChargingSessionModel, session_id)
    assert row.total_energy_kwh is None
    assert row.status == "ACTIVE"


@pytest.mark.asyncio
async def test_a_restart_resumes_where_sampling_stopped(sampler_session):
    """Regression: resuming from the session start re-counted the whole session.

    Six collector restarts inflated a 29 kWh session to 131 kWh, because each
    one made the next sample span the entire session and re-read the meter
    delta from the opening reading.
    """
    session, site, charger, session_id = sampler_session
    service = EVSessionService()
    runtime = service.get_runtime_state(charger.id)
    runtime.last_meter_kwh = 100.0
    runtime.last_sample_at = STARTED
    sampler = EVSessionSampler(service)
    for cumulative, minutes in ((102.0, 1), (104.0, 2)):
        await sampler.sample_active_session(
            session,
            charger=charger,
            site=site,
            meter=_meter(cumulative, minutes=minutes),
            energy_sample=_grid_sample(),
            is_sqlite=True,
        )

    # A restart drops the in-memory state, then resume rebuilds it.
    restarted = EVSessionService()
    await restarted.resume_active_sessions(session)
    resumed = restarted.get_runtime_state(charger.id)

    assert resumed.last_sample_at == STARTED + timedelta(minutes=2)
    assert resumed.last_meter_kwh is None

    # The first sample after the restart adds only the gap, not the session.
    await EVSessionSampler(restarted).sample_active_session(
        session,
        charger=charger,
        site=site,
        meter=_meter(104.5, minutes=3),
        energy_sample=_grid_sample(),
        is_sqlite=True,
    )

    row = await session.get(EvChargingSessionModel, session_id)
    assert row.total_energy_kwh < 5.0, "a restart must not re-count the session"


@pytest.mark.asyncio
async def test_a_resume_without_intervals_falls_back_to_the_session_start(sampler_session):
    session, _site, charger, _session_id = sampler_session
    service = EVSessionService()

    await service.resume_active_sessions(session)

    state = service.get_runtime_state(charger.id)
    assert state.last_sample_at == STARTED
    assert state.last_vehicle_connected is True


@pytest.mark.asyncio
async def test_no_active_session_means_nothing_is_written(sampler_session):
    session, site, charger, session_id = sampler_session
    await EvChargingSessionRepository(session).complete(session_id, total_energy_kwh=7.0)
    service = EVSessionService()
    runtime = service.get_runtime_state(charger.id)
    runtime.last_meter_kwh = 100.0
    runtime.last_sample_at = STARTED
    sampler = EVSessionSampler(service)

    await sampler.sample_active_session(
        session,
        charger=charger,
        site=site,
        meter=_meter(102.0, minutes=1),
        energy_sample=_grid_sample(),
        is_sqlite=True,
    )

    row = await session.get(EvChargingSessionModel, session_id)
    assert row.status == "COMPLETED"
    assert abs(row.total_energy_kwh - 7.0) < 0.01
