"""Vehicle integration supervisor tests."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from energy_core.config import Settings
from energy_core.db.models import Base, VehicleProviderConnectionModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.models import SiteModel
from energy_core.vehicles.supervisor import VehicleIntegrationSupervisor


@pytest.mark.asyncio
async def test_supervisor_start_and_stop(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "supervisor.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Akarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        session.add(
            VehicleProviderConnectionModel(site_id=site.id, enabled=True, username="user@example.com")
        )
        await session.commit()

    supervisor = VehicleIntegrationSupervisor(session_factory, settings)
    await supervisor.start()
    await supervisor.stop()
    await engine.dispose()
