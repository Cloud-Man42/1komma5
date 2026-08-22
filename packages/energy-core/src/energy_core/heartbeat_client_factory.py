"""Async factory for HeartBeat clients with token refresh."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.heartbeat_client import HeartbeatClient, build_heartbeat_client
from energy_core.heartbeat_connection import HeartbeatConnectionType


async def create_heartbeat_client(session: AsyncSession) -> HeartbeatClient | None:
    """Build a client using a valid token, refreshing from password when needed."""
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
