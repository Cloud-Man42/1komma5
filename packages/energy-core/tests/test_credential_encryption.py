"""Tests for encrypted integration credential storage."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from energy_core.config import Settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import Base, EvChargerModel, SiteModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.secrets import CredentialCipher, SecretBox


@pytest.fixture
async def credential_session(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("EMIC_SECRET_KEY", key)
    db_file = tmp_path / "credentials.db"
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
async def test_ev_charger_repo_encrypts_api_key(credential_session):
    session_factory, site_id = credential_session
    async with session_factory() as session:
        repo = EvChargerRepository(session)
        charger = await repo.create(site_id, name="Halo", chargeamps_api_key="secret-key")
        assert charger.chargeamps_api_key != "secret-key"
        assert repo.decrypt_chargeamps_api_key(charger) == "secret-key"
        await session.commit()


@pytest.mark.asyncio
async def test_heartbeat_repo_encrypts_password_and_token(credential_session):
    session_factory, _site_id = credential_session
    async with session_factory() as session:
        repo = HeartbeatSettingsRepository(session)
        await repo.update(
            connection_type="cloud",
            host="heartbeat.example.com",
            port=443,
            use_tls=True,
            api_path="/api",
            poll_interval_seconds=60,
            dashboard_refresh_seconds=30,
            username="user@example.com",
            password="heartbeat-pass",
            api_token="legacy-token",
        )
        row = await repo.get_or_create()
        assert row.password != "heartbeat-pass"
        assert row.api_token != "legacy-token"
        password, token = await repo.get_secrets()
        assert password == "heartbeat-pass"
        assert token == "legacy-token"
        await session.commit()


@pytest.mark.asyncio
async def test_consumer_repo_encrypts_spa_api_key(credential_session):
    session_factory, site_id = credential_session
    async with session_factory() as session:
        site = await session.get(SiteModel, site_id)
        consumer_repo = ConsumerRepository(session)
        _consumer, config = await consumer_repo.get_or_create_spa(site)
        await consumer_repo.update_spa_config(config.consumer_id, api_key="spa-secret")
        assert config.api_key != "spa-secret"
        assert consumer_repo.decrypt_spa_api_key(config) == "spa-secret"
        await session.commit()


def test_credential_cipher_legacy_plaintext_fallback(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    cipher = CredentialCipher()
    assert cipher.decrypt("legacy-plaintext") == "legacy-plaintext"


def test_credential_cipher_does_not_double_encrypt(monkeypatch):
    monkeypatch.setenv("EMIC_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    box = SecretBox.from_settings()
    cipher = CredentialCipher(box)
    once = cipher.encrypt("secret")
    twice = cipher.encrypt(once)
    assert twice == once
    assert cipher.decrypt(twice) == "secret"
