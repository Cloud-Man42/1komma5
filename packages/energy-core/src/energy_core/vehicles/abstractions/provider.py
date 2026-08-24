"""Vehicle provider protocols."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from energy_core.vehicles.abstractions.models import VehicleCommandResult, VehicleState, VehicleStateChangedEvent


@runtime_checkable
class VehicleProvider(Protocol):
    @property
    def provider_id(self) -> str: ...

    async def connect(self) -> None: ...

    async def get_vehicles(self) -> tuple[VehicleState, ...]: ...

    def watch_vehicle_state(self) -> AsyncIterator[VehicleStateChangedEvent]: ...

    async def close(self) -> None: ...


@runtime_checkable
class VehicleCommandProvider(Protocol):
    async def set_target_soc(self, vehicle_id: str, target_soc: int) -> VehicleCommandResult: ...

    async def start_charging(self, vehicle_id: str) -> VehicleCommandResult: ...

    async def stop_charging(self, vehicle_id: str) -> VehicleCommandResult: ...
