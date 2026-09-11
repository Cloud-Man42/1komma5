"""Reference demo module for Step 5A package tests."""

from __future__ import annotations

from energy_core.platform.modules.sdk.context import EmicModuleContext
from energy_core.platform.modules.sdk.health import HealthStatus
from energy_core.platform.modules.sdk.protocols import EmicModuleRuntime


class DemoModuleRuntime:
    def __init__(self, *, fail_health: bool = False, label: str = "demo") -> None:
        self._fail_health = fail_health
        self._label = label
        self._started = False

    def start(self, ctx: EmicModuleContext) -> None:
        self._started = True

    def stop(self, ctx: EmicModuleContext) -> None:
        self._started = False

    def health(self) -> HealthStatus:
        if self._fail_health:
            return HealthStatus.unhealthy("simulated bad health")
        return HealthStatus.ok(f"{self._label} running")


def build_module(context: EmicModuleContext) -> EmicModuleRuntime:
    config = dict(context.configuration)
    fail_health = bool(config.get("fail_health", False))
    label = str(config.get("label", "demo"))
    return DemoModuleRuntime(fail_health=fail_health, label=label)
