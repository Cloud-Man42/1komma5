"""Tests for Mercedes REST vehicle sync."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from energy_core.config import Settings
from energy_core.db.models import Base, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle
from energy_core.vehicles.sync_service import VehicleSyncError, VehicleSyncService


@pytest.fixture
async def sync_session(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "vehicle-sync.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        site = SiteModel(slug="akarp", name="Åkarp", timezone="Europe/Stockholm")
        session.add(site)
        await session.flush()
        provider_repo = VehicleProviderRepository(session)
        row = await provider_repo.get_or_create(site.id)
        await provider_repo.update_config(row, enabled=True, username="user@example.com", password="secret")
        await provider_repo.persist_token_bundle(
            row,
            MercedesTokenBundle(
                access_token="access",
                refresh_token="refresh",
                expires_at=9_999_999_999,
                device_guid="device-guid",
                session_id="session-id",
            ),
        )
        await session.commit()
        yield session_factory, site.id
    await engine.dispose()


def _synced_state() -> VehicleState:
    now = datetime.now(UTC)
    return VehicleState(
        vehicle_id="W1KEG2CB0SF063146",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE",
        vin="W1KEG2CB0SF063146",
        state_of_charge_percent=72.0,
        electric_range_km=430.0,
        is_plugged_in=False,
        is_charging=False,
        connection_state=VehicleConnectionState.CONNECTED,
        data_quality=DataQuality.MEASURED,
        last_vehicle_update=now,
        last_provider_update=now,
        capabilities=VehicleCapabilities(can_read_soc=True),
    )


@pytest.mark.asyncio
async def test_sync_site_persists_fresh_mercedes_state(sync_session):
    session_factory, site_id = sync_session
    synced = (_synced_state(),)

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        await repo.upsert_vehicle(
            site_id=site_id,
            provider="mercedes",
            external_id="W1KEG2CB0SF063146",
            vin="W1KEG2CB0SF063146",
            manufacturer="Mercedes-Benz",
            model="EQE",
            display_name="EQE",
        )
        await session.commit()

    with patch("energy_core.vehicles.sync_service.MercedesProvider") as provider_cls:
        provider = AsyncMock()
        provider.sync_from_rest = AsyncMock(return_value=synced)
        provider.close = AsyncMock()
        provider_cls.return_value = provider

        async with session_factory() as session:
            result = await VehicleSyncService(session, is_sqlite=True).sync_site(site_id)
            await session.commit()

    assert len(result) == 1
    assert result[0].is_plugged_in is False

    async with session_factory() as session:
        repo = VehicleRepository(session, is_sqlite=True)
        vehicle = await repo.get_by_external_id(
            site_id=site_id,
            provider="mercedes",
            external_id="W1KEG2CB0SF063146",
        )
        assert vehicle is not None
        latest = await repo.get_latest_state(vehicle.id)
        assert latest is not None
        assert latest.is_plugged_in is False
        assert latest.state_of_charge_percent == 72.0


@pytest.mark.asyncio
async def test_sync_site_rejects_disabled_integration(sync_session):
    session_factory, site_id = sync_session
    async with session_factory() as session:
        provider_repo = VehicleProviderRepository(session)
        row = await provider_repo.get_for_site(site_id)
        assert row is not None
        row.enabled = False
        with pytest.raises(VehicleSyncError, match="not enabled"):
            await VehicleSyncService(session, is_sqlite=True).sync_site(site_id)
