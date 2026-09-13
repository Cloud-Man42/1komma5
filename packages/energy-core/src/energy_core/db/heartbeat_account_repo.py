"""Persistence for multi-account Heartbeat credentials."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import HeartbeatAccountModel, SiteModel
from energy_core.integrations.heartbeat.auth import (
    HeartbeatAuthError,
    humanize_auth_error,
    jwt_expires_at,
    refresh_bearer_token,
    token_needs_refresh,
)
from energy_core.integrations.heartbeat.connection import (
    CLOUD_HOST,
    CLOUD_PORT,
    DEFAULT_API_PATH,
    HeartbeatConnectionType,
    apply_provider_defaults,
    build_account_api_url,
)
from energy_core.integrations.heartbeat.auth_probe import AuthProbeResult
from energy_core.integrations.heartbeat.gridx_auth import (
    gridx_token_needs_refresh,
    login_gridx_token_set,
    refresh_gridx_token_set_async,
)
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider
from energy_core.integrations.heartbeat.token_service import refresh_lock_for
from energy_core.secrets import CredentialCipher

logger = logging.getLogger(__name__)

DEFAULT_ACCOUNT_SLUG = "default"


@dataclass(frozen=True, slots=True)
class HeartbeatAccountRecord:
    id: int
    slug: str
    name: str
    provider: str
    connection_type: str
    host: str
    port: int
    use_tls: bool
    api_path: str
    auth_domain: str
    auth_realm: str
    auth_client_id: str
    username: str
    password_configured: bool
    api_token_configured: bool
    refresh_token_configured: bool
    api_url: str | None
    token_expires_at: datetime | None
    is_enabled: bool
    last_authentication_at: datetime | None
    last_successful_authentication_at: datetime | None
    last_api_call_at: datetime | None
    last_successful_api_call_at: datetime | None
    last_authentication_error: str | None
    updated_at: datetime | None


class HeartbeatAccountRepository:
    def __init__(self, session: AsyncSession, *, credential_cipher: CredentialCipher | None = None) -> None:
        self._session = session
        self._credentials = credential_cipher or CredentialCipher()

    async def list_accounts(self, *, enabled_only: bool = False) -> list[HeartbeatAccountRecord]:
        stmt = select(HeartbeatAccountModel).order_by(HeartbeatAccountModel.name)
        if enabled_only:
            stmt = stmt.where(HeartbeatAccountModel.is_enabled.is_(True))
        rows = await self._session.scalars(stmt)
        return [self._to_record(row) for row in rows]

    async def get_by_id(self, account_id: int) -> HeartbeatAccountModel | None:
        return await self._session.get(HeartbeatAccountModel, account_id)

    async def get_by_slug(self, slug: str) -> HeartbeatAccountModel | None:
        return await self._session.scalar(
            select(HeartbeatAccountModel).where(HeartbeatAccountModel.slug == slug.strip())
        )

    async def get_default_account(self) -> HeartbeatAccountModel | None:
        return await self.get_by_slug(DEFAULT_ACCOUNT_SLUG)

    async def get_record(self, account_id: int) -> HeartbeatAccountRecord:
        row = await self.get_by_id(account_id)
        if row is None:
            raise KeyError(account_id)
        await self._session.refresh(row)
        return self._to_record(row)

    async def create(
        self,
        *,
        slug: str,
        name: str,
        provider: str = HeartbeatBackendProvider.ONEKOMMAFIVE.value,
        connection_type: str = HeartbeatConnectionType.CLOUD.value,
        host: str = "",
        port: int = CLOUD_PORT,
        use_tls: bool = True,
        api_path: str = DEFAULT_API_PATH,
        auth_domain: str = "",
        auth_realm: str = "",
        auth_client_id: str = "",
        username: str = "",
        password: str | None = None,
        is_enabled: bool = True,
    ) -> HeartbeatAccountRecord:
        host, port, api_path, auth_domain, auth_realm, auth_client_id = apply_provider_defaults(
            provider,
            host=host,
            port=port,
            api_path=api_path,
            auth_domain=auth_domain,
            auth_realm=auth_realm,
            auth_client_id=auth_client_id,
        )
        row = HeartbeatAccountModel(
            slug=slug.strip(),
            name=name.strip(),
            provider=provider,
            connection_type=connection_type,
            host=host,
            port=port,
            use_tls=use_tls,
            api_path=api_path,
            auth_domain=auth_domain,
            auth_realm=auth_realm,
            auth_client_id=auth_client_id,
            username=username.strip(),
            password=self._credentials.encrypt(password or ""),
            is_enabled=is_enabled,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def update(
        self,
        account_id: int,
        *,
        name: str | None = None,
        provider: str | None = None,
        connection_type: str | None = None,
        host: str | None = None,
        port: int | None = None,
        use_tls: bool | None = None,
        api_path: str | None = None,
        auth_domain: str | None = None,
        auth_realm: str | None = None,
        auth_client_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
        api_token: str | None = None,
        is_enabled: bool | None = None,
    ) -> HeartbeatAccountRecord:
        row = await self.get_by_id(account_id)
        if row is None:
            raise KeyError(account_id)
        if name is not None:
            row.name = name.strip()
        if provider is not None:
            row.provider = provider
        if connection_type is not None:
            row.connection_type = connection_type
        if host is not None:
            row.host = host.strip()
        if port is not None:
            row.port = port
        if use_tls is not None:
            row.use_tls = use_tls
        if api_path is not None:
            row.api_path = api_path.strip()
        if auth_domain is not None:
            row.auth_domain = auth_domain.strip()
        if auth_realm is not None:
            row.auth_realm = auth_realm.strip()
        if auth_client_id is not None:
            row.auth_client_id = auth_client_id.strip()
        if username is not None:
            row.username = username.strip()
        if password is not None:
            row.password = self._credentials.encrypt(password)
        if api_token is not None:
            row.api_token = self._credentials.encrypt(api_token)
            exp = jwt_expires_at(api_token)
            row.token_expires_at = datetime.fromtimestamp(exp, tz=UTC) if exp else None
        if is_enabled is not None:
            row.is_enabled = is_enabled

        host, port, api_path, auth_domain, auth_realm, auth_client_id = apply_provider_defaults(
            row.provider,
            host=row.host,
            port=row.port,
            api_path=row.api_path,
            auth_domain=row.auth_domain,
            auth_realm=row.auth_realm,
            auth_client_id=row.auth_client_id,
        )
        row.host = host
        row.port = port
        row.api_path = api_path
        row.auth_domain = auth_domain
        row.auth_realm = auth_realm
        row.auth_client_id = auth_client_id
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(row)

    async def apply_auth_probe(self, account_id: int, probe: AuthProbeResult) -> HeartbeatAccountRecord:
        row = await self.get_by_id(account_id)
        if row is None:
            raise KeyError(account_id)
        row.provider = probe.provider
        row.connection_type = probe.connection_type
        row.host = probe.host
        row.port = probe.port
        row.use_tls = probe.use_tls
        row.api_path = probe.api_path
        row.auth_domain = probe.auth_domain
        row.auth_realm = probe.auth_realm
        row.auth_client_id = probe.auth_client_id
        row.api_token = self._credentials.encrypt(probe.access_token)
        row.refresh_token = self._credentials.encrypt(probe.refresh_token or "")
        row.token_expires_at = probe.token_expires_at
        row.last_authentication_at = datetime.now(UTC)
        row.last_successful_authentication_at = datetime.now(UTC)
        row.last_authentication_error = None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return self._to_record(row)

    async def record_api_call(self, account_id: int, *, success: bool) -> None:
        row = await self.get_by_id(account_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row.last_api_call_at = now
        if success:
            row.last_successful_api_call_at = now
        row.updated_at = now
        await self._session.flush()

    async def disable_account(self, account_id: int) -> HeartbeatAccountRecord:
        return await self.update(account_id, is_enabled=False)

    async def get_secrets(self, account_id: int) -> tuple[str, str, str]:
        row = await self.get_by_id(account_id)
        if row is None:
            raise KeyError(account_id)
        return (
            self._credentials.decrypt(row.password),
            self._credentials.decrypt(row.api_token),
            self._credentials.decrypt(row.refresh_token),
        )

    async def ensure_api_token(self, account_id: int, *, force: bool = False) -> str:
        row = await self.get_by_id(account_id)
        if row is None:
            raise KeyError(account_id)
        if not row.is_enabled:
            raise HeartbeatAuthError(f"Heartbeat account {row.slug} is disabled")

        async with refresh_lock_for(account_id):
            row = await self.get_by_id(account_id)
            if row is None:
                raise KeyError(account_id)

            if row.connection_type == HeartbeatConnectionType.MOCK.value:
                return self._credentials.decrypt(row.api_token)

            provider = HeartbeatBackendProvider(row.provider)
            if provider == HeartbeatBackendProvider.GRIDX:
                return await self._ensure_gridx_api_token(row, force=force)
            return await self._ensure_onekommafive_api_token(row, force=force)

    async def _ensure_onekommafive_api_token(self, row: HeartbeatAccountModel, *, force: bool) -> str:
        api_token = self._credentials.decrypt(row.api_token)
        if not force and api_token and not token_needs_refresh(api_token):
            return api_token

        password = self._credentials.decrypt(row.password)
        row.last_authentication_at = datetime.now(UTC)
        if not row.username or not password:
            if api_token:
                return api_token
            row.last_authentication_error = "Missing username or password"
            await self._session.flush()
            raise HeartbeatAuthError(
                "HeartBeat Bearer-token saknas och inget lösenord finns sparat för automatisk förnyelse."
            )

        try:
            refreshed = await refresh_bearer_token(row.username, password)
        except HeartbeatAuthError as exc:
            row.last_authentication_error = humanize_auth_error(str(exc))[:512]
            await self._session.flush()
            raise

        row.api_token = self._credentials.encrypt(refreshed)
        exp = jwt_expires_at(refreshed)
        row.token_expires_at = datetime.fromtimestamp(exp, tz=UTC) if exp else None
        row.last_successful_authentication_at = datetime.now(UTC)
        row.last_authentication_error = None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        logger.info(
            "HeartBeat Bearer token refreshed",
            extra={"heartbeatAccountId": row.id, "operation": "refresh_token", "provider": row.provider},
        )
        return refreshed

    async def _ensure_gridx_api_token(self, row: HeartbeatAccountModel, *, force: bool) -> str:
        api_token = self._credentials.decrypt(row.api_token)
        refresh_token = self._credentials.decrypt(row.refresh_token)
        needs_refresh = force or not api_token or gridx_token_needs_refresh(api_token)

        if not needs_refresh:
            return api_token

        row.last_authentication_at = datetime.now(UTC)
        token_set = None
        if refresh_token and not force:
            try:
                token_set = await refresh_gridx_token_set_async(
                    refresh_token,
                    auth_domain=row.auth_domain,
                    auth_client_id=row.auth_client_id,
                )
            except HeartbeatAuthError:
                token_set = None

        password = self._credentials.decrypt(row.password)
        if token_set is None:
            if not row.username or not password:
                if api_token:
                    return api_token
                row.last_authentication_error = "Missing username or password"
                await self._session.flush()
                raise HeartbeatAuthError("GridX-token saknas och inget lösenord finns sparat.")
            try:
                token_set = await login_gridx_token_set(
                    row.username,
                    password,
                    auth_domain=row.auth_domain,
                    auth_realm=row.auth_realm,
                    auth_client_id=row.auth_client_id,
                )
            except HeartbeatAuthError as exc:
                row.last_authentication_error = humanize_auth_error(str(exc))[:512]
                await self._session.flush()
                raise

        row.api_token = self._credentials.encrypt(token_set.access_token)
        if token_set.refresh_token:
            row.refresh_token = self._credentials.encrypt(token_set.refresh_token)
        exp = jwt_expires_at(token_set.access_token)
        row.token_expires_at = datetime.fromtimestamp(exp, tz=UTC) if exp else None
        row.last_successful_authentication_at = datetime.now(UTC)
        row.last_authentication_error = None
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        logger.info(
            "GridX Bearer token refreshed",
            extra={"heartbeatAccountId": row.id, "operation": "refresh_token", "provider": row.provider},
        )
        return token_set.access_token

    async def resolve_account_for_site(self, site: SiteModel) -> HeartbeatAccountModel | None:
        if site.heartbeat_account_id is not None:
            account = await self.get_by_id(site.heartbeat_account_id)
            if account is not None and account.is_enabled:
                return account
        return await self.get_default_account()

    @staticmethod
    def resolve_system_id(site: SiteModel) -> str | None:
        for value in (site.heartbeat_system_id, site.external_system_id):
            if value and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def resolve_gateway_id(site: SiteModel) -> str | None:
        value = getattr(site, "heartbeat_gateway_id", None)
        if value and str(value).strip():
            return str(value).strip()
        return None

    def _to_record(self, row: HeartbeatAccountModel) -> HeartbeatAccountRecord:
        host, port, api_path, auth_domain, auth_realm, auth_client_id = apply_provider_defaults(
            row.provider,
            host=row.host,
            port=row.port,
            api_path=row.api_path,
            auth_domain=row.auth_domain,
            auth_realm=row.auth_realm,
            auth_client_id=row.auth_client_id,
        )
        connection_type = HeartbeatConnectionType(row.connection_type)
        display_host = host
        if (
            connection_type == HeartbeatConnectionType.CLOUD
            and row.provider == HeartbeatBackendProvider.ONEKOMMAFIVE.value
            and not row.host
        ):
            display_host = CLOUD_HOST
        return HeartbeatAccountRecord(
            id=row.id,
            slug=row.slug,
            name=row.name,
            provider=row.provider,
            connection_type=row.connection_type,
            host=display_host,
            port=port,
            use_tls=row.use_tls,
            api_path=api_path,
            auth_domain=auth_domain,
            auth_realm=auth_realm,
            auth_client_id=auth_client_id,
            username=row.username,
            password_configured=CredentialCipher.is_configured(row.password),
            api_token_configured=CredentialCipher.is_configured(row.api_token),
            refresh_token_configured=CredentialCipher.is_configured(row.refresh_token),
            api_url=build_account_api_url(
                row.provider,
                connection_type,
                host=host,
                port=port,
                use_tls=row.use_tls,
                api_path=api_path,
            ),
            token_expires_at=row.token_expires_at,
            is_enabled=row.is_enabled,
            last_authentication_at=row.last_authentication_at,
            last_successful_authentication_at=row.last_successful_authentication_at,
            last_api_call_at=row.last_api_call_at,
            last_successful_api_call_at=row.last_successful_api_call_at,
            last_authentication_error=row.last_authentication_error,
            updated_at=row.updated_at,
        )
