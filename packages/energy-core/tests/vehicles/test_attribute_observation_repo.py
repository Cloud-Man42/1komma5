"""Tests for vehicle attribute observation repository."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from energy_core.config import Settings
from energy_core.db.attribute_observation_repo import VehicleAttributeObservationRepository
from energy_core.db.models import Base, SiteModel, VehicleModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.vehicles.mercedes.mapping.observer import AttributeObservation


@pytest.fixture
async def observation_session(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "attr-obs.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="test-site", name="Test", timezone="UTC")
        session.add(site)
        await session.flush()
        vehicle = VehicleModel(
            site_id=site.id,
            provider="mercedes",
            external_id="vin123",
            manufacturer="Mercedes-Benz",
            model="EQE 500",
            display_name="EQE",
        )
        session.add(vehicle)
        await session.commit()
        yield session_factory, site.id, vehicle.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_and_list_observations(observation_session):
    session_factory, _site_id, vehicle_id = observation_session
    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        await repo.record_observations(
            vehicle_id,
            [AttributeObservation("soc", "WS", "int", "72")],
        )
        await session.commit()

    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        listed = await repo.list_for_vehicle(vehicle_id)
        assert len(listed) == 1
        assert listed[0].attribute_name == "soc"
        assert listed[0].sample_count == 1

    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        await repo.record_observations(
            vehicle_id,
            [AttributeObservation("soc", "WS", "int", "73")],
        )
        await session.commit()

    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        listed = await repo.list_for_vehicle(vehicle_id)
        assert listed[0].sample_count == 2
        assert listed[0].masked_sample == "73"


@pytest.mark.asyncio
async def test_list_for_site(observation_session):
    session_factory, site_id, vehicle_id = observation_session
    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        await repo.record_observations(
            vehicle_id,
            [AttributeObservation("chargingpowerkw", "REST", "float", "11.0")],
        )
        await session.commit()

    async with session_factory() as session:
        repo = VehicleAttributeObservationRepository(session, is_sqlite=True)
        rows = await repo.list_for_site(site_id)
        assert len(rows) == 1
        assert rows[0][0] == vehicle_id
        assert rows[0][1].attribute_name == "chargingpowerkw"
