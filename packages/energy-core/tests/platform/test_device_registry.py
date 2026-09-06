"""Device registry projection tests."""

import pytest
from cryptography.fernet import Fernet
from energy_core.config import Settings
from energy_core.db.models import Base, EvChargerModel, SiteModel, VehicleModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.platform.devices.registry import DeviceRegistry, DeviceType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def registry_session(tmp_path, monkeypatch) -> AsyncSession:
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "device-registry.db"
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
            EvChargerModel(
                site_id=site.id,
                name="Halo",
                manufacturer="ChargeAmps",
                model="Halo",
                bridge_enabled=True,
                integration_method="CHARGE_AMPS_CLOUD",
            )
        )
        session.add(
            VehicleModel(
                site_id=site.id,
                provider="mercedes",
                external_id="veh-1",
                display_name="EQE",
                enabled=True,
            )
        )
        await session.commit()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_device_registry_lists_charger_and_vehicle(registry_session: AsyncSession) -> None:
    site_id = (await registry_session.execute(select(SiteModel.id).where(SiteModel.slug == "akarp"))).scalar_one()
    records = await DeviceRegistry(registry_session).list_for_site(site_id)
    types = {record.device_id.device_type for record in records}
    assert DeviceType.EV_CHARGER in types
    assert DeviceType.VEHICLE in types


@pytest.mark.asyncio
async def test_device_registry_empty_site_returns_empty_tuple(registry_session: AsyncSession) -> None:
    records = await DeviceRegistry(registry_session).list_for_site(site_id=99999)
    assert records == ()
