"""PostgreSQL row-level security session binding."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings


async def bind_tenant_to_session(
    session: AsyncSession,
    settings: Settings,
    *,
    tenant_id: int | None,
    platform_bypass: bool = False,
) -> None:
    if settings.is_sqlite:
        return
    bind = session.bind
    if bind is None or bind.dialect.name != "postgresql":
        return
    if platform_bypass:
        await session.execute(text("SELECT set_config('app.platform_bypass', 'true', true)"))
        return
    if tenant_id is None:
        await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
        return
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def reset_rls_session(session: AsyncSession, settings: Settings) -> None:
    if settings.is_sqlite:
        return
    bind = session.bind
    if bind is None or bind.dialect.name != "postgresql":
        return
    await session.execute(text("RESET ALL"))
