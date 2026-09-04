"""ChargeFinder integration health sync in collector slow lane."""

from __future__ import annotations

import pytest
from energy_core.config import Settings
from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRepository
from energy_core.db.models import Base, IntegrationHealthModel, SiteModel, VehicleProviderConnectionModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.integrations.health import IntegrationHealthRecorder
from sqlalchemy import select

from collector.app.collector import Collector


@pytest.mark.asyncio
async def test_chargefinder_health_sync_records_per_vehicle_site(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CHARGEFINDER_ENABLED", "true")
    monkeypatch.setenv("CHARGEFINDER_MODE", "WEB")

    db_file = tmp_path / "chargefinder-health.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Akarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        site_id = site.id
        session.add(VehicleProviderConnectionModel(site_id=site_id, enabled=True, username="user@example.com"))
        status_repo = ChargeFinderIntegrationStatusRepository(session)
        await status_repo.record_success(latency_ms=42)
        await session.commit()

    collector = Collector()
    collector._settings = settings
    collector._session_factory = session_factory

    async with session_factory() as session:
        await collector._sync_chargefinder_health(session)
        await session.commit()

        rows = (
            await session.scalars(
                select(IntegrationHealthModel).where(IntegrationHealthModel.provider == "chargefinder")
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].site_id == site_id
        assert rows[0].status == "ok"
        assert rows[0].latency_ms == 42.0

    await engine.dispose()


@pytest.mark.asyncio
async def test_chargefinder_health_sync_skips_when_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CHARGEFINDER_ENABLED", "false")

    db_file = tmp_path / "chargefinder-disabled.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    collector = Collector()
    collector._settings = settings
    collector._session_factory = session_factory

    async with session_factory() as session:
        await collector._sync_chargefinder_health(session)
        recorder = IntegrationHealthRecorder(session, is_sqlite=True)
        assert await recorder.list_for_site(1) == []

    await engine.dispose()
