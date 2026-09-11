"""Module runtime lifecycle handlers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Protocol

from energy_core.config import Settings

logger = logging.getLogger(__name__)

ModuleHandler = Callable[["ModuleRuntimeContext"], Coroutine[Any, Any, None]]


@dataclass(slots=True)
class ModuleRuntimeContext:
    session_factory: Any
    settings: Settings
    site_id: int
    module_id: str
    cancel_event: Any
    extras: dict[str, Any]


class IModuleRuntimeHandler(Protocol):
    module_id: str

    async def start(self, ctx: ModuleRuntimeContext) -> None: ...

    async def stop(self, ctx: ModuleRuntimeContext) -> None: ...


class LaneModuleHandler:
    """No-op handler for lane-gated modules; registry state drives collector skips."""

    def __init__(self, module_id: str) -> None:
        self.module_id = module_id

    async def start(self, ctx: ModuleRuntimeContext) -> None:
        logger.info("WorkerStarted site_id=%s module_id=%s", ctx.site_id, ctx.module_id)

    async def stop(self, ctx: ModuleRuntimeContext) -> None:
        logger.info("WorkerStopped site_id=%s module_id=%s", ctx.site_id, ctx.module_id)


_handler_registry: dict[str, IModuleRuntimeHandler] = {}


def register_module_handler(handler: IModuleRuntimeHandler) -> None:
    _handler_registry[handler.module_id] = handler


def get_module_handler(module_id: str) -> IModuleRuntimeHandler | None:
    return _handler_registry.get(module_id)


def list_module_handlers() -> tuple[str, ...]:
    return tuple(sorted(_handler_registry.keys()))


def register_default_module_handlers(*, vehicle_supervisor: Any | None = None) -> None:
    """Register built-in handlers. Idempotent for repeated calls."""
    lane_modules = (
        "integration.heartbeat",
        "integration.chargeamps",
        "integration.mercedes",
        "integration.arctic_spa",
        "integration.chargefinder",
        "integration.smhi",
        "integration.dmi",
        "integration.open_meteo",
        "feature.smart-charging",
        "feature.solar-forecast",
        "feature.energy-balance",
        "feature.spa-energy",
        "feature.price-engine",
        "feature.energy-control",
        "feature.vehicles",
    )
    for module_id in lane_modules:
        if module_id not in _handler_registry:
            register_module_handler(LaneModuleHandler(module_id))

    if vehicle_supervisor is not None and "integration.mercedes" not in _handler_registry:
        register_module_handler(MercedesSupervisorHandler(vehicle_supervisor))


class MercedesSupervisorHandler:
    module_id = "integration.mercedes"

    def __init__(self, supervisor: Any) -> None:
        self._supervisor = supervisor

    async def start(self, ctx: ModuleRuntimeContext) -> None:
        await self._supervisor.start_site(ctx.site_id)
        logger.info("WorkerStarted site_id=%s module_id=%s", ctx.site_id, self.module_id)

    async def stop(self, ctx: ModuleRuntimeContext) -> None:
        await self._supervisor.stop_site(ctx.site_id)
        logger.info("WorkerStopped site_id=%s module_id=%s", ctx.site_id, self.module_id)
