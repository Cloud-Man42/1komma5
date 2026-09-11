"""Energy-layer access to Heartbeat client construction."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.integrations.heartbeat.client import HeartbeatClient


async def open_heartbeat_client(session: AsyncSession) -> HeartbeatClient | None:
    """Return a configured Heartbeat client or None when unavailable."""
    from energy_core.integrations.heartbeat.client_factory import create_heartbeat_client

    return await create_heartbeat_client(session)
