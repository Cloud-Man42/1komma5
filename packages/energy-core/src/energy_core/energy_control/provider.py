"""Control provider protocol."""

from __future__ import annotations

from typing import Protocol

from energy_core.energy_control.types import ControlResult, ControlTarget, OptimizationAction


class IEnergyControlProvider(Protocol):
    provider_name: str

    async def apply_action(
        self,
        *,
        site_id: int,
        action: OptimizationAction,
        target: ControlTarget,
        dry_run: bool,
        context: dict | None = None,
    ) -> ControlResult: ...
