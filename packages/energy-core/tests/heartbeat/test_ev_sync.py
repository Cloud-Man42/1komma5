"""Tests for Heartbeat EV sync service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.db.models import EvChargerModel, HeartbeatSettingsModel, SiteModel
from energy_core.heartbeat.ev_sync import HeartbeatEvSyncService, _remote_wins


@pytest.fixture
async def sync_session(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet

    from energy_core.config import Settings
    from energy_core.db.models import Base
    from energy_core.db.session import create_engine, create_session_factory

    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "heartbeat-sync.db"
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL=f"sqlite+aiosqlite:///{db_file.as_posix()}")
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_push_charger_updates_heartbeat_and_metadata(sync_session):
    async with sync_session() as session:
        site = SiteModel(slug="akarp", name="Akarp", timezone="Europe/Stockholm", external_system_id="sys-1")
        session.add(site)
        await session.flush()
        settings = HeartbeatSettingsModel(id=1, connection_type="cloud", heartbeat_write_enabled=True)
        session.add(settings)
        charger = EvChargerModel(
            site_id=site.id,
            name="Halo",
            heartbeat_ev_id="ev-1",
            heartbeat_sync_enabled=True,
            charging_mode="SMART_CHARGE",
            target_soc_pct=80.0,
            departure_time="07:00",
        )
        session.add(charger)
        await session.commit()

        client = AsyncMock()
        service = HeartbeatEvSyncService(session)
        with patch("energy_core.heartbeat.ev_sync.create_heartbeat_client", AsyncMock(return_value=client)):
            result = await service.push_charger(charger, site)

        assert result.pushed is True
        client.update_ev_charge_settings.assert_awaited_once()
        assert charger.heartbeat_last_pushed_at is not None
        assert charger.heartbeat_sync_error is None


def test_remote_wins_after_cooldown():
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    charger = EvChargerModel(
        site_id=1,
        name="Halo",
        heartbeat_last_pushed_at=now - timedelta(minutes=5),
        heartbeat_remote_updated_at=now - timedelta(minutes=10),
        charging_mode="SMART_CHARGE",
        target_soc_pct=70.0,
    )
    remote = MagicMock()
    remote.remote_updated_at = now - timedelta(minutes=1)
    remote.charging_mode = "PRICE_CHARGE"
    remote.target_soc_pct = 70.0
    remote.departure_time = None
    assert _remote_wins(charger, remote, now=now) is True


def test_remote_does_not_win_during_push_cooldown():
    now = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    charger = EvChargerModel(
        site_id=1,
        name="Halo",
        heartbeat_last_pushed_at=now - timedelta(seconds=10),
        charging_mode="SMART_CHARGE",
        target_soc_pct=70.0,
    )
    remote = MagicMock()
    remote.remote_updated_at = now
    remote.charging_mode = "PRICE_CHARGE"
    remote.target_soc_pct = 70.0
    remote.departure_time = None
    assert _remote_wins(charger, remote, now=now) is False
