"""Provider protocol for external charging station lookup."""

from __future__ import annotations

from typing import Protocol

from energy_core.integrations.charging_stations.models import ChargingStationCandidate


class IChargingStationProvider(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def find_stations(
        self,
        *,
        latitude: float,
        longitude: float,
        radius_m: int,
        limit: int = 10,
    ) -> list[ChargingStationCandidate]: ...
