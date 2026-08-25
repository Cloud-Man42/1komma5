"""Vehicle SoC provider abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class VehicleSocSnapshot:
    soc_pct: float
    source: str
    vehicle_id: str | None = None


class IVehicleSocProvider(Protocol):
    async def get_soc(self, vehicle_id: str) -> VehicleSocSnapshot | None: ...


class IHeartbeatVehicleSocProvider(Protocol):
    async def update_manual_soc(self, ev_id: str, soc_pct: float) -> dict[str, object]: ...
