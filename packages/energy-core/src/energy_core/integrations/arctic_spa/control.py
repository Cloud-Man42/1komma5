"""Future smart spa control interfaces."""

from __future__ import annotations

from typing import Protocol

from energy_core.integrations.arctic_spa.models import ArcticSpaStatus


class ISpaControlService(Protocol):
    async def get_status(self) -> ArcticSpaStatus: ...

    async def set_target_temperature_c(self, temperature_c: float) -> None: ...

    async def set_pump_state(self, pump: int, state: str) -> None: ...
