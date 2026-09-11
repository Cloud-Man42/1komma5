"""Apply module configuration to runtime (distributed restart via pub/sub)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.cache.module_pubsub import publish_module_restart
from energy_core.config import Settings, get_settings
from energy_core.platform.modules.aliases import resolve_module_id
from energy_core.platform.modules.registry import default_module_registry
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.platform.modules.sync_state import mark_site_modules_dirty
from energy_core.platform.modules.types import RuntimeStatus


@dataclass(frozen=True, slots=True)
class ModuleApplyResult:
    module_id: str
    success: bool
    message: str
    runtime_status: str
    health_status: str


class ModuleApplyService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    async def apply_module(self, site_id: int, module_id: str) -> ModuleApplyResult:
        canonical = resolve_module_id(module_id)
        if default_module_registry.get(canonical) is None:
            raise ValueError("Module not found")
        resolver = SiteModuleResolver(self._session, settings=self._settings)
        modules = await resolver.list_modules(site_id)
        state = next((item for item in modules if item.module_id == canonical), None)
        if state is None:
            raise ValueError("Module not found for site")
        if not state.enabled:
            return ModuleApplyResult(
                module_id=canonical,
                success=False,
                message="Module is disabled; enable before applying configuration",
                runtime_status=state.runtime_status.value,
                health_status=state.health_status.value,
            )
        invalidate_site_module_cache(site_id)
        mark_site_modules_dirty(site_id)
        published = await publish_module_restart(self._settings, site_id, canonical)
        if not published:
            return ModuleApplyResult(
                module_id=canonical,
                success=False,
                message="Configuration saved but runtime restart could not be published (Redis unavailable)",
                runtime_status=state.runtime_status.value,
                health_status=state.health_status.value,
            )
        refreshed = await resolver.list_modules(site_id, use_cache=False)
        updated = next((item for item in refreshed if item.module_id == canonical), state)
        return ModuleApplyResult(
            module_id=canonical,
            success=True,
            message="Module restart requested; runtime will reconcile via collector",
            runtime_status=updated.runtime_status.value,
            health_status=updated.health_status.value,
        )
