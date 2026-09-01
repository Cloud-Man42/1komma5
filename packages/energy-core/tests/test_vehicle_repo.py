"""Vehicle repository tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet
from energy_core.db.models import Base, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.config import Settings


@pytest.fixture
async def vehicle_session(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "vehicles.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="test-site", name="Test", timezone="UTC")
        session.add(site)
        await session.commit()
        yield session_factory, site.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_provider_repo_encrypts_password(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleProviderRepository(session)
        row = await repo.get_or_create(site_id)
        await repo.update_config(row, username="user@example.com", password="secret-pass")
        assert row.encrypted_password != "secret-pass"
        assert repo.decrypt_password(row) == "secret-pass"
        await session.commit()


@pytest.mark.asyncio
async def test_upsert_capabilities_is_idempotent(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        vehicle = await repo.upsert_vehicle(
            site_id=site_id,
            provider="mock",
            external_id="mock-cap",
            vin="W1K12345678901234",
            manufacturer="Mercedes-Benz",
            model="EQE",
            display_name="EQE",
        )
        caps = VehicleCapabilities(can_read_soc=True, can_start_charging=True)
        await repo.upsert_capabilities(vehicle.id, caps)
        await repo.upsert_capabilities(vehicle.id, caps)
        await session.commit()


@pytest.mark.asyncio
async def test_load_token_bundle_generates_session_id(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleProviderRepository(session)
        row = await repo.get_or_create(site_id)
        row.encrypted_access_token = repo._secrets.encrypt("access")  # noqa: SLF001
        row.encrypted_refresh_token = repo._secrets.encrypt("refresh")  # noqa: SLF001
        row.session_id = ""
        bundle = repo.load_token_bundle(row)
        assert bundle is not None
        assert bundle.session_id
        assert len(bundle.session_id) >= 32


@pytest.mark.asyncio
async def test_set_enabled_clears_charger_link(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        vehicle = await repo.upsert_vehicle(
            site_id=site_id,
            provider="mercedes",
            external_id="glc",
            vin="WDC12345678902594",
            manufacturer="Mercedes-Benz",
            model="GLC",
            display_name="GLC",
        )
        vehicle.charger_id = 4
        await repo.set_enabled(vehicle.id, enabled=False)
        assert vehicle.enabled is False
        assert vehicle.charger_id is None
        await session.commit()


@pytest.mark.asyncio
async def test_vehicle_state_history_on_change(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        vehicle = await repo.upsert_vehicle(
            site_id=site_id,
            provider="mock",
            external_id="mock-1",
            vin="W1K12345678901234",
            manufacturer="Mercedes-Benz",
            model="EQE",
            display_name="EQE",
        )
        now = datetime.now(UTC)
        state = VehicleState(
            vehicle_id="mock-1",
            provider="mock",
            manufacturer="Mercedes-Benz",
            model="EQE",
            state_of_charge_percent=30.0,
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=DataQuality.MEASURED,
            last_vehicle_update=now,
            capabilities=VehicleCapabilities(can_read_soc=True),
        )
        await repo.persist_state(vehicle.id, state)
        updated = VehicleState(
            vehicle_id="mock-1",
            provider="mock",
            manufacturer="Mercedes-Benz",
            model="EQE",
            state_of_charge_percent=31.0,
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=DataQuality.MEASURED,
            last_vehicle_update=now,
            capabilities=VehicleCapabilities(can_read_soc=True),
        )
        await repo.persist_state(vehicle.id, updated)
        latest = await repo.get_latest_state(vehicle.id)
        assert latest is not None
        assert latest.state_of_charge_percent == 31.0
        await session.commit()


def _measured_state(now: datetime) -> VehicleState:
    return VehicleState(
        vehicle_id="mock-1",
        provider="mock",
        manufacturer="Mercedes-Benz",
        model="EQE",
        state_of_charge_percent=100.0,
        electric_range_km=604.0,
        is_plugged_in=True,
        is_charging=False,
        connection_state=VehicleConnectionState.CONNECTED,
        data_quality=DataQuality.MEASURED,
        last_vehicle_update=now,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )


def _discovery_state(
    connection_state: VehicleConnectionState = VehicleConnectionState.CONNECTED,
) -> VehicleState:
    """What MercedesProvider.discover returns: identity, no telemetry."""
    return VehicleState(
        vehicle_id="mock-1",
        provider="mock",
        manufacturer="Mercedes-Benz",
        model="EQE",
        connection_state=connection_state,
        data_quality=DataQuality.UNKNOWN,
        last_provider_update=datetime.now(UTC),
        capabilities=VehicleCapabilities(can_read_soc=True),
    )


@pytest.fixture
async def stored_vehicle(vehicle_session):
    session_factory, site_id = vehicle_session
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        vehicle = await repo.upsert_vehicle(
            site_id=site_id,
            provider="mock",
            external_id="mock-1",
            vin="W1K12345678901234",
            manufacturer="Mercedes-Benz",
            model="EQE",
            display_name="EQE",
        )
        await session.commit()
        yield session_factory, vehicle.id


@pytest.mark.asyncio
async def test_a_discovery_does_not_blank_a_good_reading(stored_vehicle):
    """Every collector restart used to wipe the car's state to OFFLINE."""
    session_factory, vehicle_id = stored_vehicle
    now = datetime.now(UTC)
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _measured_state(now))
        await session.commit()

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _discovery_state())
        await session.commit()

    async with session_factory() as session:
        latest = await VehicleRepository(session, is_sqlite=True).get_latest_state(vehicle_id)
        assert latest is not None
        assert latest.state_of_charge_percent == 100.0
        assert latest.electric_range_km == 604.0
        assert latest.is_plugged_in is True
        assert latest.data_quality == "MEASURED"
        assert latest.last_vehicle_update is not None


@pytest.mark.asyncio
async def test_a_discovery_still_refreshes_the_link_state(stored_vehicle):
    session_factory, vehicle_id = stored_vehicle
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _measured_state(datetime.now(UTC)))
        await session.commit()

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _discovery_state(VehicleConnectionState.DEGRADED))
        await session.commit()

    async with session_factory() as session:
        latest = await VehicleRepository(session, is_sqlite=True).get_latest_state(vehicle_id)
        assert latest is not None
        assert latest.connection_state == "DEGRADED"
        assert latest.state_of_charge_percent == 100.0


@pytest.mark.asyncio
async def test_a_first_discovery_creates_the_row_even_without_telemetry(stored_vehicle):
    session_factory, vehicle_id = stored_vehicle
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _discovery_state())
        await session.commit()

    async with session_factory() as session:
        latest = await VehicleRepository(session, is_sqlite=True).get_latest_state(vehicle_id)
        assert latest is not None
        assert latest.data_quality == "UNKNOWN"
        assert latest.state_of_charge_percent is None


@pytest.mark.asyncio
async def test_a_real_reading_still_overwrites_an_older_one(stored_vehicle):
    session_factory, vehicle_id = stored_vehicle
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _measured_state(datetime.now(UTC)))
        await session.commit()

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        newer = VehicleState(
            vehicle_id="mock-1",
            provider="mock",
            manufacturer="Mercedes-Benz",
            model="EQE",
            state_of_charge_percent=42.0,
            electric_range_km=250.0,
            is_plugged_in=False,
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=DataQuality.MEASURED,
            last_vehicle_update=datetime.now(UTC),
            capabilities=VehicleCapabilities(can_read_soc=True),
        )
        await repo.persist_state(vehicle_id, newer)
        await session.commit()

    async with session_factory() as session:
        latest = await VehicleRepository(session, is_sqlite=True).get_latest_state(vehicle_id)
        assert latest is not None
        assert latest.state_of_charge_percent == 42.0
        assert latest.electric_range_km == 250.0
        assert latest.is_plugged_in is False


@pytest.mark.asyncio
async def test_not_charging_signal_clears_stale_plugged_state(stored_vehicle):
    session_factory, vehicle_id = stored_vehicle
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _measured_state(datetime.now(UTC)))
        await session.commit()

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        idle = VehicleState(
            vehicle_id="mock-1",
            provider="mock",
            manufacturer="Mercedes-Benz",
            model="EQE",
            state_of_charge_percent=100.0,
            electric_range_km=604.0,
            is_plugged_in=None,
            is_charging=False,
            charging_power_kw=0.0,
            connection_state=VehicleConnectionState.CONNECTED,
            data_quality=DataQuality.MEASURED,
            last_vehicle_update=datetime.now(UTC),
            capabilities=VehicleCapabilities(can_read_soc=True),
        )
        await repo.persist_state(vehicle_id, idle)
        await session.commit()

    async with session_factory() as session:
        latest = await VehicleRepository(session, is_sqlite=True).get_latest_state(vehicle_id)
        assert latest is not None
        assert latest.is_plugged_in is False


@pytest.mark.asyncio
async def test_a_discovery_writes_no_history_row(stored_vehicle):
    session_factory, vehicle_id = stored_vehicle
    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _measured_state(datetime.now(UTC)))
        await session.commit()

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.persist_state(vehicle_id, _discovery_state())
        await session.commit()

    async with session_factory() as session:
        from sqlalchemy import func, select as sa_select

        from energy_core.db.models import VehicleStateHistoryModel

        total = await session.execute(
            sa_select(func.count()).select_from(VehicleStateHistoryModel).where(
                VehicleStateHistoryModel.vehicle_id == vehicle_id
            )
        )
        assert total.scalar_one() == 1
