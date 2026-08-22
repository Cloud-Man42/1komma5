"""Energy provider abstraction."""

from __future__ import annotations

from typing import Protocol

from energy_core.energy.state import EnergyState


class EnergyProvider(Protocol):
    async def get_energy_state(self) -> EnergyState: ...
