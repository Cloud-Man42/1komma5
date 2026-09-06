"""Module lifecycle phases."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable, Coroutine

LifecycleHandler = Callable[[], Coroutine[Any, Any, None]]


class LifecyclePhase(StrEnum):
    REGISTER = "register"
    INITIALIZE = "initialize"
    START = "start"
    STOP = "stop"
    HEALTH_CHECK = "health_check"


class ModuleLifecycle:
    """Thin lifecycle wrapper for async module hooks."""

    def __init__(self) -> None:
        self._handlers: dict[LifecyclePhase, list[LifecycleHandler]] = {
            phase: [] for phase in LifecyclePhase
        }

    def on(self, phase: LifecyclePhase, handler: LifecycleHandler) -> None:
        self._handlers[phase].append(handler)

    async def run(self, phase: LifecyclePhase) -> None:
        for handler in self._handlers[phase]:
            await handler()
