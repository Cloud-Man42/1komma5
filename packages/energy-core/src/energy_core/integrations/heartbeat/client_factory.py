"""Async factory for HeartBeat / GridX clients with per-account token refresh."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.heartbeat_account_repo import HeartbeatAccountRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.models import SiteModel
from energy_core.integrations.heartbeat.auth import HeartbeatAuthError
from energy_core.integrations.heartbeat.client import HeartbeatClient, build_heartbeat_client
from energy_core.integrations.heartbeat.connection import HeartbeatConnectionType
from energy_core.integrations.heartbeat.gridx_client import GridXClient, build_gridx_client
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider

logger = logging.getLogger(__name__)

HeartbeatApiClient = HeartbeatClient | GridXClient


async def create_heartbeat_client(
    session: AsyncSession,
    *,
    account_id: int | None = None,
) -> HeartbeatApiClient | None:
    """Build a client for one Heartbeat account, refreshing token when needed."""
    account_repo = HeartbeatAccountRepository(session)

    if account_id is not None:
        return await _client_for_account(session, account_repo, account_id)

    default_account = await account_repo.get_default_account()
    if default_account is not None:
        return await _client_for_account(session, account_repo, default_account.id)

    return await _legacy_client(session)


async def create_heartbeat_client_for_site(
    session: AsyncSession,
    site: SiteModel,
) -> HeartbeatApiClient | None:
    """Build a client using the Heartbeat account bound to a site."""
    account_repo = HeartbeatAccountRepository(session)
    account = await account_repo.resolve_account_for_site(site)
    if account is None:
        return await _legacy_client(session)
    return await _client_for_account(session, account_repo, account.id)


async def create_heartbeat_clients_by_account(session: AsyncSession) -> dict[int, HeartbeatApiClient]:
    """Build enabled account clients keyed by account id."""
    account_repo = HeartbeatAccountRepository(session)
    clients: dict[int, HeartbeatApiClient] = {}
    for record in await account_repo.list_accounts(enabled_only=True):
        if record.connection_type == HeartbeatConnectionType.MOCK.value:
            continue
        try:
            client = await _client_for_account(session, account_repo, record.id)
        except HeartbeatAuthError as exc:
            logger.warning(
                "Skipping Heartbeat account %s: authentication failed",
                record.slug,
                extra={"heartbeatAccountId": record.id, "error": str(exc)[:200]},
            )
            continue
        if client is not None:
            clients[record.id] = client
    if clients:
        return clients

    legacy = await _legacy_client(session)
    if legacy is not None:
        default_account = await account_repo.get_default_account()
        if default_account is not None:
            clients[default_account.id] = legacy
    return clients


async def _client_for_account(
    session: AsyncSession,
    account_repo: HeartbeatAccountRepository,
    account_id: int,
) -> HeartbeatApiClient | None:
    record = await account_repo.get_record(account_id)
    if record.connection_type == HeartbeatConnectionType.MOCK.value:
        return None

    api_token = await account_repo.ensure_api_token(account_id)
    password, _, _ = await account_repo.get_secrets(account_id)

    async def refresh_token() -> str:
        return await account_repo.ensure_api_token(account_id, force=True)

    refresh: Callable[[], Awaitable[str]] | None = refresh_token
    if not password and not record.username:
        refresh = None

    if record.provider == HeartbeatBackendProvider.GRIDX.value:
        return build_gridx_client(
            host=record.host,
            port=record.port,
            use_tls=record.use_tls,
            api_token=api_token,
            refresh_token=refresh,
            account_id=account_id,
        )

    return build_heartbeat_client(
        connection_type=record.connection_type,
        host=record.host,
        port=record.port,
        use_tls=record.use_tls,
        api_path=record.api_path,
        api_token=api_token,
        username=record.username,
        password=password,
        refresh_token=refresh,
        account_id=account_id,
    )


async def _legacy_client(session: AsyncSession) -> HeartbeatClient | None:
    """Backward-compatible path when heartbeat_accounts is empty."""
    repo = HeartbeatSettingsRepository(session)
    record = await repo.get_record()
    if record.connection_type == HeartbeatConnectionType.MOCK.value:
        return None

    api_token = await repo.ensure_api_token()
    password, _ = await repo.get_secrets()

    async def refresh_token() -> str:
        return await repo.ensure_api_token(force=True)

    refresh: Callable[[], Awaitable[str]] | None = refresh_token
    if not password and not record.username:
        refresh = None

    return build_heartbeat_client(
        connection_type=record.connection_type,
        host=record.host,
        port=record.port,
        use_tls=record.use_tls,
        api_path=record.api_path,
        api_token=api_token,
        username=record.username,
        password=password,
        refresh_token=refresh,
    )
