"""Collector module gating helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.platform.modules.aliases import resolve_module_id
from energy_core.platform.modules.runtime_registry import default_module_runtime_registry
from energy_core.platform.modules.site_modules import SiteModuleResolver
from energy_core.platform.modules.types import RuntimeStatus


async def is_collector_module_enabled(
    session: AsyncSession,
    site_id: int,
    module_id: str,
    *,
    settings: Settings | None = None,
) -> bool:
    return await is_module_runtime_active(session, site_id, module_id, settings=settings)


async def is_module_runtime_active(
    session: AsyncSession,
    site_id: int,
    module_id: str,
    *,
    settings: Settings | None = None,
) -> bool:
    resolved_settings = settings or get_settings()
    if not resolved_settings.module_gate_enabled:
        return True
    canonical = resolve_module_id(module_id)
    resolver = SiteModuleResolver(session, settings=resolved_settings)
    if not await resolver.is_module_active(site_id, canonical):
        return False
    state = default_module_runtime_registry.get_state(site_id, canonical)
    return state == RuntimeStatus.RUNNING


async def filter_sites_for_module(
    session: AsyncSession,
    sites: list,
    module_id: str,
    *,
    settings: Settings | None = None,
) -> list:
    resolved_settings = settings or get_settings()
    if not resolved_settings.module_gate_enabled:
        return sites
    filtered = []
    for site in sites:
        if await is_module_runtime_active(session, site.id, module_id, settings=resolved_settings):
            filtered.append(site)
    return filtered


async def any_site_module_runtime_active(
    session: AsyncSession,
    sites: list,
    module_id: str,
    *,
    settings: Settings | None = None,
) -> bool:
    for site in sites:
        if await is_module_runtime_active(session, site.id, module_id, settings=settings):
            return True
    return False
