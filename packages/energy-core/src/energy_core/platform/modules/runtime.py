"""In-memory module runtime state."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from energy_core.platform.modules.types import ModuleHealthStatus, RuntimeStatus


@dataclass
class ModuleRuntimeState:
    runtime_status: RuntimeStatus = RuntimeStatus.STOPPED
    health_status: ModuleHealthStatus = ModuleHealthStatus.UNKNOWN
    last_error: str | None = None
    last_health_check_at: float | None = None


@dataclass
class ModuleRuntimeStore:
    _states: dict[tuple[int, str], ModuleRuntimeState] = field(default_factory=dict)

    def get(self, site_id: int, module_id: str) -> ModuleRuntimeState:
        key = (site_id, module_id)
        if key not in self._states:
            self._states[key] = ModuleRuntimeState()
        return self._states[key]

    def set_runtime(self, site_id: int, module_id: str, status: RuntimeStatus, *, error: str | None = None) -> None:
        state = self.get(site_id, module_id)
        state.runtime_status = status
        if error is not None:
            state.last_error = error

    def set_health(self, site_id: int, module_id: str, status: ModuleHealthStatus) -> None:
        state = self.get(site_id, module_id)
        state.health_status = status
        state.last_health_check_at = time.monotonic()

    def clear_site(self, site_id: int) -> None:
        keys = [key for key in self._states if key[0] == site_id]
        for key in keys:
            del self._states[key]


default_module_runtime_store = ModuleRuntimeStore()

# Provider string -> module_id mapping for integration health
INTEGRATION_PROVIDER_MODULE_MAP: dict[str, str] = {
    "heartbeat": "integration.heartbeat",
    "price_engine": "feature.price-engine",
    "solar_forecast": "feature.solar-forecast",
    "arctic_spa": "integration.arctic_spa",
    "energy_control": "feature.energy-control",
    "mercedes": "integration.mercedes",
    "chargefinder": "integration.chargefinder",
    "chargeamps": "integration.chargeamps",
}
