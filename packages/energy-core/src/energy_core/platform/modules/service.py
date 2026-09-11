"""Site module mutation service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.cache.module_pubsub import publish_module_state_change
from energy_core.config import Settings, get_settings
from energy_core.platform.modules.aliases import resolve_module_id
from energy_core.platform.modules.orchestrator import ModuleOrchestrator
from energy_core.platform.modules.site_modules import SiteModuleResolver, SiteModuleState, invalidate_site_module_cache
from energy_core.platform.modules.sync_state import mark_site_modules_dirty


class SiteModuleService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        session_factory: object | None = None,
        orchestrator: ModuleOrchestrator | None = None,
        apply_runtime: bool = False,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._resolver = SiteModuleResolver(session, settings=self._settings)
        self._apply_runtime = apply_runtime
        self._orchestrator = orchestrator
        if apply_runtime and orchestrator is None:
            self._orchestrator = ModuleOrchestrator(
                session,
                settings=self._settings,
                session_factory=session_factory,
            )

    async def set_enabled(self, site_id: int, module_id: str, enabled: bool) -> SiteModuleState:
        canonical = resolve_module_id(module_id)
        state = await self._resolver.persist_enabled_override(site_id, canonical, enabled)
        invalidate_site_module_cache(site_id)
        mark_site_modules_dirty(site_id)
        await publish_module_state_change(self._settings, site_id, canonical, enabled)

        if self._apply_runtime and self._orchestrator is not None:
            if enabled:
                await self._orchestrator.start_module(site_id, canonical)
            else:
                await self._orchestrator.stop_module(site_id, canonical)

        modules = await self._resolver.list_modules(site_id, use_cache=False)
        for item in modules:
            if item.module_id == canonical:
                return item
        return state
