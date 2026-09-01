"""Tests for vehicle integration event repository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet
from energy_core.config import Settings
from energy_core.db.integration_event_repo import VehicleIntegrationEventRepository
from energy_core.db.models import Base, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleRepository
from energy_core.vehicles.diagnostics.events import (
    IntegrationEventDraft,
    IntegrationEventSeverity,
    IntegrationEventType,
)


@pytest.fixture
async def event_session(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "events.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Akarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.commit()
        await session.refresh(site)
        vehicle = await VehicleRepository(session, is_sqlite=True).upsert_vehicle(
            site_id=site.id,
            provider="mercedes",
            external_id="vin-1",
            vin="W1K12345678901234",
            manufacturer="Mercedes-Benz",
            model="EQE",
            display_name="EQE",
        )
        await session.commit()
        yield session_factory, site.id, vehicle.id
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_and_list_integration_events(event_session):
    session_factory, site_id, vehicle_id = event_session
    async with session_factory() as session:
        repo = VehicleIntegrationEventRepository(session)
        await repo.record_events(
            site_id=site_id,
            vehicle_id=vehicle_id,
            events=(
                IntegrationEventDraft(
                    event_type=IntegrationEventType.SOC_UPDATED,
                    severity=IntegrationEventSeverity.INFO,
                    message="SoC updated to 37%",
                    details={"new_soc": 37},
                    recorded_at=datetime.now(UTC),
                ),
            ),
        )
        await session.commit()

    async with session_factory() as session:
        events = await VehicleIntegrationEventRepository(session).list_recent(site_id=site_id)
        assert len(events) == 1
        assert events[0].event_type == "SOC_UPDATED"
        assert "37" in events[0].message
