"""Solar forecasting contracts."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession


@runtime_checkable
class ISolarForecastCoordinator(Protocol):
    async def refresh_site_now(self, session: AsyncSession, site) -> bool: ...

    async def run_due_sites(self, session: AsyncSession, sites: list) -> int: ...
