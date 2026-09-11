"""Climate API tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.deps import set_session_factory
from app.main import create_app
from energy_core.climate.repository import ClimateStateRepository
from energy_core.config import Settings
from energy_core.contracts.climate.status import ClimateDeviceState
from energy_core.db.models import Base
from energy_core.seed import seed_sites
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture
async def climate_client(tmp_path):
    db_file = tmp_path / "climate-api.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
        EMIC_ADMIN_TOKEN="admin-secret",
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        await ClimateStateRepository(session).upsert_reading(
            site_id=1,
            module_id="integration.sensibo",
            state=ClimateDeviceState(
                device_id="pod1",
                site_id=1,
                observed_at=datetime.now(UTC),
                temperature_c=21.0,
                humidity_percent=40.0,
                online=True,
                vendor="Sensibo",
            ),
        )
        await session.commit()
    app = create_app(settings)
    set_session_factory(session_factory, settings)
    transport = ASGITransport(app=app)
    headers = {"Authorization": "Bearer admin-secret"}
    async with AsyncClient(transport=transport, base_url="http://test", headers=headers) as client:
        yield client
    await engine.dispose()


@pytest.mark.asyncio
async def test_list_climate_devices(climate_client):
    response = await climate_client.get("/api/sites/akarp/climate/devices")
    assert response.status_code == 200
    body = response.json()
    assert body["devices"][0]["device_id"] == "pod1"
    assert body["devices"][0]["temperature_c"] == 21.0


@pytest.mark.asyncio
async def test_hvac_section_from_climate_readings(climate_client, tmp_path):
    db_file = tmp_path / "hvac-section.db"
    settings = Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}",
    )
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_sites(session)
        repo = ClimateStateRepository(session)
        await repo.upsert_reading(
            site_id=1,
            module_id="integration.sensibo",
            state=ClimateDeviceState(
                device_id="pod1",
                site_id=1,
                observed_at=datetime.now(UTC),
                online=True,
                vendor="Sensibo",
            ),
        )
        section = await repo.hvac_section_for_site(1)
        assert section.state == "online"
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_climate_device_not_found(climate_client):
    response = await climate_client.get("/api/sites/akarp/climate/devices/missing")
    assert response.status_code == 404
