"""Tesla Fleet API vehicle provider."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from energy_core.vehicles.abstractions.models import VehicleState, VehicleStateChangedEvent


class TeslaClientProtocol(Protocol):
    async def get_vehicle_states(self) -> tuple[VehicleState, ...]: ...


class TeslaFleetVehicleProvider:
    provider_id = "tesla"

    def __init__(self, *, client: TeslaClientProtocol, mock: bool) -> None:
        self._client = client
        self._mock = mock
        self._closed = False
        self._states: dict[str, VehicleState] = {}

    async def connect(self) -> None:
        for state in await self._client.get_vehicle_states():
            self._states[state.vehicle_id] = state

    async def get_vehicles(self) -> tuple[VehicleState, ...]:
        if not self._states:
            await self.connect()
        return tuple(self._states.values())

    async def watch_vehicle_state(self) -> AsyncIterator[VehicleStateChangedEvent]:
        if False:
            yield VehicleStateChangedEvent(state=None)  # pragma: no cover
        try:
            while not self._closed:
                for state in await self._client.get_vehicle_states():
                    previous = self._states.get(state.vehicle_id)
                    self._states[state.vehicle_id] = state
                    if previous != state:
                        yield VehicleStateChangedEvent(state=state, previous_state=previous)
                await asyncio.sleep(30 if not self._mock else 3600)
        except asyncio.CancelledError:
            return

    async def close(self) -> None:
        self._closed = True


class TeslaStubVehicleProvider(TeslaFleetVehicleProvider):
    """Backward-compatible alias for the previous stub name."""

    def __init__(self) -> None:
        from energy_core.integrations.tesla.mock import TeslaMockClient

        super().__init__(client=TeslaMockClient(), mock=True)
