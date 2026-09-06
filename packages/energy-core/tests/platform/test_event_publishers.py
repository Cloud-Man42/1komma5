"""Tests for domain event publishers at state transition points."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.contracts.devices.meter import MeterSnapshot
from energy_core.db.models import Base, EvChargerModel, IntegrationHealthModel, SiteModel, VehicleModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.config import Settings
from energy_core.ev_accounting.session_service import EVSessionService
from energy_core.integrations.health import IntegrationHealthRecorder
from energy_core.platform.events.bus import ChargingEventBus, DomainEvent, reset_event_bus, set_event_bus
from energy_core.platform.events.types import (
    CHARGING_SESSION_STARTED,
    CHARGING_SESSION_STOPPED,
    INTEGRATION_HEALTH_CHANGED,
    VEHICLE_STATE_CHANGED,
)
from energy_core.db.vehicle_repo import VehicleRepository
from energy_core.vehicles.abstractions.models import (
    DataQuality,
    VehicleCapabilities,
    VehicleConnectionState,
    VehicleState,
)


@pytest.fixture
def event_capture():
    bus = ChargingEventBus()
    captured: list[DomainEvent] = []

    def _capture(event: DomainEvent) -> None:
        captured.append(event)

    for name in (
        CHARGING_SESSION_STARTED,
        CHARGING_SESSION_STOPPED,
        VEHICLE_STATE_CHANGED,
        INTEGRATION_HEALTH_CHANGED,
    ):
        bus.subscribe(name, _capture)

    set_event_bus(bus)
    yield captured
    reset_event_bus()


@pytest.fixture
async def sqlite_session(tmp_path):
    db_file = tmp_path / "events.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session, settings
    await engine.dispose()


def _connected_meter(**kwargs) -> MeterSnapshot:
    defaults = {
        "recorded_at": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        "cumulative_kwh": 12.5,
        "power_w": 7000.0,
        "configured_current_a": 16.0,
        "actual_charging_current_a": 16.0,
        "is_charging": True,
        "vehicle_connected": True,
        "ocpp_status": "Charging",
        "phase_current_l1_a": 16.0,
        "phase_current_l2_a": 16.0,
        "phase_current_l3_a": 16.0,
        "energy_source": "meter",
    }
    defaults.update(kwargs)
    return MeterSnapshot(**defaults)


@pytest.mark.asyncio
async def test_ev_session_start_publishes_domain_event(sqlite_session, event_capture):
    session, _settings = sqlite_session
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    session.add(site)
    await session.flush()
    charger = EvChargerModel(site_id=site.id, name="Halo", manufacturer="ChargeAmps", model="Halo")
    session.add(charger)
    await session.flush()

    service = EVSessionService()
    meter = _connected_meter(vehicle_connected=True)
    session_id = await service.process_charger(session, charger=charger, site=site, meter=meter)

    assert session_id is not None
    assert len(event_capture) == 1
    assert event_capture[0].name == CHARGING_SESSION_STARTED
    assert event_capture[0].payload["session_kind"] == "ev"
    assert event_capture[0].payload["site_id"] == site.id
    assert event_capture[0].payload["session_id"] == session_id


@pytest.mark.asyncio
async def test_ev_session_stop_publishes_domain_event(sqlite_session, event_capture):
    session, _settings = sqlite_session
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    session.add(site)
    await session.flush()
    charger = EvChargerModel(site_id=site.id, name="Halo", manufacturer="ChargeAmps", model="Halo")
    session.add(charger)
    await session.flush()

    service = EVSessionService()
    start_meter = _connected_meter(vehicle_connected=True, cumulative_kwh=10.0)
    await service.process_charger(session, charger=charger, site=site, meter=start_meter)
    stop_meter = _connected_meter(vehicle_connected=False, cumulative_kwh=15.0)
    await service.process_charger(session, charger=charger, site=site, meter=stop_meter)

    stopped = [event for event in event_capture if event.name == CHARGING_SESSION_STOPPED]
    assert len(stopped) == 1
    assert stopped[0].payload["session_kind"] == "ev"
    assert stopped[0].payload["charger_id"] == charger.id


@pytest.mark.asyncio
async def test_integration_health_change_publishes_domain_event(sqlite_session, event_capture):
    session, settings = sqlite_session
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    session.add(site)
    await session.flush()

    recorder = IntegrationHealthRecorder(session, is_sqlite=settings.is_sqlite)
    await recorder.record_success(site.id, "heartbeat")
    await session.commit()

    await recorder.record_failure(site.id, "heartbeat", error_class="TimeoutError")
    await session.commit()

    health_events = [event for event in event_capture if event.name == INTEGRATION_HEALTH_CHANGED]
    assert len(health_events) == 2
    assert health_events[0].payload["previous_status"] is None
    assert health_events[0].payload["status"] == "ok"
    assert health_events[1].payload["previous_status"] == "ok"
    assert health_events[1].payload["status"] == "error"


@pytest.mark.asyncio
async def test_vehicle_state_change_publishes_domain_event(sqlite_session, event_capture):
    session, settings = sqlite_session
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    session.add(site)
    await session.flush()
    vehicle = VehicleModel(
        site_id=site.id,
        provider="mercedes",
        external_id="veh-1",
        vin="VIN123",
        manufacturer="Mercedes",
        model="EQE",
        display_name="EQE",
    )
    session.add(vehicle)
    await session.commit()

    repo = VehicleRepository(session, is_sqlite=settings.is_sqlite)
    now = datetime.now(UTC)
    base = dict(
        vehicle_id="veh-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE",
        state_of_charge_percent=50,
        data_quality=DataQuality.MEASURED,
        last_vehicle_update=now,
        last_provider_update=now,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )
    await repo.persist_state(
        vehicle.id,
        VehicleState(
            **base,
            is_plugged_in=False,
            is_charging=False,
            connection_state=VehicleConnectionState.DISCONNECTED,
        ),
    )
    await repo.persist_state(
        vehicle.id,
        VehicleState(
            **base,
            is_plugged_in=True,
            is_charging=False,
            connection_state=VehicleConnectionState.CONNECTED,
        ),
    )

    vehicle_events = [event for event in event_capture if event.name == VEHICLE_STATE_CHANGED]
    assert len(vehicle_events) == 1
    assert vehicle_events[0].payload["vehicle_id"] == vehicle.id
    assert vehicle_events[0].payload["previous_plugged_in"] is False
    assert vehicle_events[0].payload["is_plugged_in"] is True


@pytest.mark.asyncio
async def test_integration_health_unchanged_status_does_not_publish(sqlite_session, event_capture):
    session, settings = sqlite_session
    site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
    session.add(site)
    await session.flush()

    recorder = IntegrationHealthRecorder(session, is_sqlite=settings.is_sqlite)
    await recorder.record_success(site.id, "heartbeat")
    await session.commit()
    event_capture.clear()
    await recorder.record_success(site.id, "heartbeat")
    await session.commit()

    assert event_capture == []
