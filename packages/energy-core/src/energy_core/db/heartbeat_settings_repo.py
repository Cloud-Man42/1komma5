"""Persistence for editable HeartBeat settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import HeartbeatSettingsModel, SiteModel
from energy_core.heartbeat_auth import HeartbeatAuthError, refresh_bearer_token, token_needs_refresh
from energy_core.secrets import CredentialCipher
from energy_core.heartbeat_connection import (
    CLOUD_HOST,
    CLOUD_PORT,
    DEFAULT_API_PATH,
    HeartbeatConnectionType,
    build_heartbeat_api_url,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HeartbeatSettingsRecord:
    connection_type: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    poll_interval_seconds: int
    dashboard_refresh_seconds: int
    username: str
    password_configured: bool
    api_token_configured: bool
    api_url: str | None
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class SiteHeartbeatMapping:
    slug: str
    name: str
    external_system_id: str | None


class HeartbeatSettingsRepository:
    SETTINGS_ID = 1

    def __init__(self, session: AsyncSession, *, credential_cipher: CredentialCipher | None = None) -> None:
        self._session = session
        self._credentials = credential_cipher or CredentialCipher()

    async def get_or_create(self) -> HeartbeatSettingsModel:
        row = await self._session.get(HeartbeatSettingsModel, self.SETTINGS_ID)
        if row is None:
            row = HeartbeatSettingsModel(
                id=self.SETTINGS_ID,
                connection_type=HeartbeatConnectionType.MOCK.value,
                host="",
                port=CLOUD_PORT,
                use_tls=True,
                api_path=DEFAULT_API_PATH,
                poll_interval_seconds=60,
                dashboard_refresh_seconds=30,
            )
            self._session.add(row)
            await self._session.flush()
        return row

    async def get_record(self) -> HeartbeatSettingsRecord:
        row = await self.get_or_create()
        return self._to_record(row)

    async def update(
        self,
        *,
        connection_type: str,
        host: str,
        port: int,
        use_tls: bool,
        api_path: str,
        poll_interval_seconds: int,
        dashboard_refresh_seconds: int,
        username: str,
        password: str | None = None,
        api_token: str | None = None,
    ) -> HeartbeatSettingsRecord:
        row = await self.get_or_create()
        row.connection_type = connection_type
        row.host = host.strip()
        row.port = port
        row.use_tls = use_tls
        row.api_path = api_path.strip() or DEFAULT_API_PATH
        row.poll_interval_seconds = poll_interval_seconds
        row.dashboard_refresh_seconds = dashboard_refresh_seconds
        row.username = username.strip()
        if password is not None:
            row.password = self._credentials.encrypt(password)
        if api_token is not None:
            row.api_token = self._credentials.encrypt(api_token)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(row)

    async def list_site_mappings(self) -> list[SiteHeartbeatMapping]:
        from sqlalchemy import select

        sites = await self._session.scalars(select(SiteModel).order_by(SiteModel.name))
        return [
            SiteHeartbeatMapping(
                slug=site.slug,
                name=site.name,
                external_system_id=site.external_system_id,
            )
            for site in sites
        ]

    async def update_site_system_id(self, slug: str, external_system_id: str | None) -> SiteHeartbeatMapping:
        from sqlalchemy import select

        site = await self._session.scalar(select(SiteModel).where(SiteModel.slug == slug))
        if site is None:
            raise KeyError(slug)
        site.external_system_id = external_system_id.strip() or None if external_system_id else None
        await self._session.flush()
        return SiteHeartbeatMapping(
            slug=site.slug,
            name=site.name,
            external_system_id=site.external_system_id,
        )

    @staticmethod
    def _to_record(row: HeartbeatSettingsModel) -> HeartbeatSettingsRecord:
        connection_type = HeartbeatConnectionType(row.connection_type)
        host = row.host
        if connection_type == HeartbeatConnectionType.CLOUD and not host:
            host = CLOUD_HOST

        return HeartbeatSettingsRecord(
            connection_type=row.connection_type,
            host=host,
            port=row.port,
            use_tls=row.use_tls,
            api_path=row.api_path,
            poll_interval_seconds=row.poll_interval_seconds,
            dashboard_refresh_seconds=row.dashboard_refresh_seconds,
            username=row.username,
            password_configured=CredentialCipher.is_configured(row.password),
            api_token_configured=CredentialCipher.is_configured(row.api_token),
            api_url=build_heartbeat_api_url(
                connection_type,
                host=host,
                port=row.port,
                use_tls=row.use_tls,
                api_path=row.api_path,
            ),
            updated_at=row.updated_at,
        )

    async def get_secrets(self) -> tuple[str, str]:
        row = await self.get_or_create()
        return self._credentials.decrypt(row.password), self._credentials.decrypt(row.api_token)

    async def ensure_api_token(self, *, force: bool = False) -> str:
        """Return a usable Bearer token, refreshing from password when needed."""
        row = await self.get_or_create()
        if row.connection_type == HeartbeatConnectionType.MOCK.value:
            return self._credentials.decrypt(row.api_token)

        stored_token = row.api_token
        api_token = self._credentials.decrypt(stored_token)
        if not force and api_token and not token_needs_refresh(api_token):
            return api_token

        password = self._credentials.decrypt(row.password)
        if not row.username or not password:
            if api_token:
                return api_token
            raise HeartbeatAuthError(
                "HeartBeat Bearer-token saknas och inget lösenord finns sparat för automatisk förnyelse."
            )

        refreshed = await refresh_bearer_token(row.username, password)
        row.api_token = self._credentials.encrypt(refreshed)
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        logger.info("HeartBeat Bearer token refreshed for user %s", row.username)
        return refreshed
