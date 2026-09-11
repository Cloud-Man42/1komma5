"""Generic vehicle command provider contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VehicleCommandDispatchResult:
    state: str
    detail: str = ""


class IVehicleCommandProvider(Protocol):
    async def load_command_features(self, vin: str) -> object: ...

    async def set_target_soc(
        self,
        vin: str,
        *,
        target_soc_percent: int,
        features: object,
    ) -> VehicleCommandDispatchResult: ...

    async def start_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult: ...

    async def stop_charging(self, vin: str, *, features: object) -> VehicleCommandDispatchResult: ...
