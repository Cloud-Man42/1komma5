"""Central registry of actual module runtime handles per site."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from energy_core.platform.modules.types import RuntimeStatus


@dataclass
class ModuleRuntimeHandle:
    site_id: int
    module_id: str
    state: RuntimeStatus = RuntimeStatus.STOPPED
    task: asyncio.Task | None = None
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    started_at: float | None = None
    last_error: str | None = None

    @property
    def is_running(self) -> bool:
        return self.state == RuntimeStatus.RUNNING

    @property
    def worker_count(self) -> int:
        if self.state != RuntimeStatus.RUNNING:
            return 0
        if self.task is not None and not self.task.done():
            return 1
        return 1


class ModuleRuntimeRegistry:
    def __init__(self) -> None:
        self._handles: dict[tuple[int, str], ModuleRuntimeHandle] = {}

    def get_handle(self, site_id: int, module_id: str) -> ModuleRuntimeHandle:
        key = (site_id, module_id)
        if key not in self._handles:
            self._handles[key] = ModuleRuntimeHandle(site_id=site_id, module_id=module_id)
        return self._handles[key]

    def get_state(self, site_id: int, module_id: str) -> RuntimeStatus:
        return self.get_handle(site_id, module_id).state

    def is_running(self, site_id: int, module_id: str) -> bool:
        return self.get_state(site_id, module_id) == RuntimeStatus.RUNNING

    def worker_count(self, site_id: int, module_id: str) -> int:
        return self.get_handle(site_id, module_id).worker_count

    def active_modules_for_site(self, site_id: int) -> tuple[str, ...]:
        return tuple(
            module_id
            for (sid, module_id), handle in self._handles.items()
            if sid == site_id and handle.state == RuntimeStatus.RUNNING
        )

    def mark_starting(self, site_id: int, module_id: str) -> ModuleRuntimeHandle:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.STARTING
        handle.last_error = None
        handle.cancel_event.clear()
        return handle

    def mark_running(self, site_id: int, module_id: str, *, task: asyncio.Task | None = None) -> None:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.RUNNING
        handle.started_at = time.monotonic()
        handle.last_error = None
        if task is not None:
            handle.task = task

    def mark_stopping(self, site_id: int, module_id: str) -> ModuleRuntimeHandle:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.STOPPING
        handle.cancel_event.set()
        return handle

    def mark_stopped(self, site_id: int, module_id: str) -> None:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.STOPPED
        handle.task = None
        handle.started_at = None
        handle.cancel_event.clear()

    def mark_blocked(self, site_id: int, module_id: str, *, reason: str | None = None) -> None:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.BLOCKED
        handle.task = None
        handle.started_at = None
        if reason:
            handle.last_error = reason

    def mark_failed(self, site_id: int, module_id: str, *, error: str) -> None:
        handle = self.get_handle(site_id, module_id)
        handle.state = RuntimeStatus.FAILED
        handle.task = None
        handle.last_error = error

    def clear_site(self, site_id: int) -> None:
        keys = [key for key in self._handles if key[0] == site_id]
        for key in keys:
            del self._handles[key]


default_module_runtime_registry = ModuleRuntimeRegistry()
