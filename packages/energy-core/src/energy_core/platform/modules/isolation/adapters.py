"""Orchestrator adapters for in-process vs isolated runtime."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.platform.modules.handlers import IModuleRuntimeHandler, ModuleRuntimeContext, get_module_handler
from energy_core.platform.modules.isolation.manager import IsolatedModuleRuntimeManager
from energy_core.platform.modules.isolation.policy import requires_isolated_runtime
from energy_core.platform.modules.isolation.types import RuntimeStartRequest
from energy_core.platform.modules.registry import ModuleDescriptor

logger = logging.getLogger(__name__)


class InProcessModuleAdapter:
    async def start(self, ctx: ModuleRuntimeContext, handler: IModuleRuntimeHandler | None = None) -> None:
        resolved = handler or get_module_handler(ctx.module_id)
        if resolved is None:
            return
        await resolved.start(ctx)

    async def stop(self, ctx: ModuleRuntimeContext, handler: IModuleRuntimeHandler | None = None) -> None:
        resolved = handler or get_module_handler(ctx.module_id)
        if resolved is None:
            return
        await resolved.stop(ctx)


class IsolatedModuleAdapter:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._manager = IsolatedModuleRuntimeManager(session, settings)

    async def start(self, ctx: ModuleRuntimeContext, *, publisher_tier: str | None) -> None:
        result = await self._manager.start_runtime(
            RuntimeStartRequest(module_id=ctx.module_id, site_id=ctx.site_id)
        )
        if not result.ok:
            logger.info(
                "Isolated runtime blocked module=%s site=%s reason=%s",
                ctx.module_id,
                ctx.site_id,
                result.message,
            )

    async def stop(self, ctx: ModuleRuntimeContext) -> None:
        runtimes = await self._manager.list_runtimes(site_id=ctx.site_id)
        for runtime in runtimes:
            if runtime.module_id == ctx.module_id and runtime.state.value not in {"STOPPED", "BLOCKED"}:
                await self._manager.stop_runtime(runtime.runtime_instance_id, reason="orchestrator stop")


def select_runtime_adapter(
    *,
    descriptor: ModuleDescriptor,
    publisher_tier: str | None,
    session: AsyncSession,
    settings: Settings,
) -> InProcessModuleAdapter | IsolatedModuleAdapter:
    if requires_isolated_runtime(descriptor, publisher_tier=publisher_tier):
        return IsolatedModuleAdapter(session, settings)
    return InProcessModuleAdapter()
