"""Vehicle provider factory tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.fernet import Fernet
from energy_core.config import Settings
from energy_core.db.models import Base, SiteModel, VehicleProviderConnectionModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.integrations.mercedes.factory import is_mercedes_provider
from energy_core.integrations.tesla.factory import is_tesla_provider
from energy_core.integrations.tesla.provider import TeslaFleetVehicleProvider
from energy_core.secrets import SecretBox
from energy_core.vehicles.mock.provider import MockVehicleProvider
from energy_core.vehicles.provider_factory import build_supervisor_provider, is_mock_vehicle_provider


@pytest.fixture
async def provider_context(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "provider-factory.db"
    settings = Settings(_env_file=None, APP_ENV="development", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Akarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        row = VehicleProviderConnectionModel(site_id=site.id, provider="mercedes", enabled=True)
        session.add(row)
        await session.commit()
        yield session_factory, settings, row
    await engine.dispose()


@pytest.mark.asyncio
async def test_build_supervisor_provider_uses_mock_in_test_env(provider_context):
    session_factory, settings, row = provider_context
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=settings.database_url)
    async with session_factory() as session:
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        provider = await build_supervisor_provider(
            row,
            repo,
            session_factory=session_factory,
            secret_box=SecretBox.from_settings(),
            settings=settings,
        )
    assert is_mock_vehicle_provider(provider)
    assert not is_mercedes_provider(provider)


@pytest.mark.asyncio
async def test_build_supervisor_provider_builds_mercedes_in_development(provider_context, monkeypatch):
    session_factory, settings, row = provider_context
    mock_provider = MagicMock()
    monkeypatch.setattr(
        "energy_core.providers.vehicle_integrations.build_mercedes_provider",
        MagicMock(return_value=mock_provider),
    )
    monkeypatch.setattr(
        "energy_core.providers.vehicle_integrations.wire_supervisor_token_callbacks",
        MagicMock(),
    )
    async with session_factory() as session:
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        provider = await build_supervisor_provider(
            row,
            repo,
            session_factory=session_factory,
            secret_box=SecretBox.from_settings(),
            settings=settings,
        )
    assert provider is mock_provider


@pytest.mark.asyncio
async def test_build_supervisor_provider_builds_tesla_stub(provider_context):
    session_factory, settings, row = provider_context
    row.provider = "tesla"
    async with session_factory() as session:
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        provider = await build_supervisor_provider(
            row,
            repo,
            session_factory=session_factory,
            secret_box=SecretBox.from_settings(),
            settings=settings,
        )
    assert isinstance(provider, TeslaFleetVehicleProvider)
    assert is_tesla_provider(provider)


@pytest.mark.asyncio
async def test_unknown_provider_raises(provider_context):
    session_factory, settings, row = provider_context
    row.provider = "bmw"
    async with session_factory() as session:
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        with pytest.raises(ValueError, match="Unknown vehicle provider"):
            await build_supervisor_provider(
                row,
                repo,
                session_factory=session_factory,
                secret_box=SecretBox.from_settings(),
                settings=settings,
            )
