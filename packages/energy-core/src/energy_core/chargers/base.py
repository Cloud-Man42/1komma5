"""Charger controller protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ChargerStatus:
    connected: bool
    vehicle_connected: bool
    current_limit_a: float | None
    charging: bool


class ChargerController(Protocol):
    async def get_status(self) -> ChargerStatus: ...

    async def set_current_limit(self, amps: float) -> None: ...

    async def start_charging(self) -> None: ...

    async def stop_charging(self) -> None: ...

    async def is_connected(self) -> bool: ...

    async def is_vehicle_connected(self) -> bool: ...
