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
