"""Scripted mock vehicle scenarios for EMIC tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from energy_core.vehicles.abstractions.models import (
    DataQuality,
    VehicleCapabilities,
    VehicleConnectionState,
    VehicleState,
    VehicleStateChangedEvent,
)


class MockVehicleScenario(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED_IDLE = "connected_idle"
    CHARGING_RAMP = "charging_ramp"
    TARGET_REACHED = "target_reached"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"
    STALE_TELEMETRY = "stale_telemetry"


_DEFAULT_CAPABILITIES = VehicleCapabilities(
    can_read_soc=True,
    can_read_range=True,
    can_read_charging_state=True,
    can_read_charging_power=True,
    can_read_target_soc=True,
    can_read_departure_time=True,
)


def _base_state(*, scenario: MockVehicleScenario) -> VehicleState:
    now = datetime.now(UTC)
    return VehicleState(
        vehicle_id="mock-eqe-500",
        provider="mock",
        manufacturer="Mercedes-Benz",
        model="EQE 500 Sedan",
        vin="W1K12345678901234",
        target_soc_percent=80.0,
        departure_time=now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1),
        capabilities=_DEFAULT_CAPABILITIES,
        last_provider_update=now,
    )


class MockVehicleProvider:
    """Simulates Mercedes EQE telemetry without cloud access."""

    provider_id = "mock"

    def __init__(
        self,
        *,
        scenario: MockVehicleScenario = MockVehicleScenario.CONNECTED_IDLE,
        tick_seconds: float = 0.05,
    ) -> None:
        self._scenario = scenario
        self._tick_seconds = tick_seconds
        self._connected = False
        self._closed = False
        self._states: dict[str, VehicleState] = {}
        self._subscribers: list[asyncio.Queue[VehicleStateChangedEvent | None]] = []

    async def connect(self) -> None:
        if self._scenario == MockVehicleScenario.BACKEND_UNAVAILABLE:
            raise RuntimeError("Mercedes backend unavailable")
        self._connected = True
        for state in self._build_initial_states():
            self._states[state.vehicle_id] = state

    async def get_vehicles(self) -> tuple[VehicleState, ...]:
        if not self._connected:
            raise RuntimeError("Mock vehicle provider is not connected")
        return tuple(self._states.values())

    async def watch_vehicle_state(self) -> AsyncIterator[VehicleStateChangedEvent]:
        if not self._connected:
            raise RuntimeError("Mock vehicle provider is not connected")
        queue: asyncio.Queue[VehicleStateChangedEvent | None] = asyncio.Queue()
        self._subscribers.append(queue)
        task = asyncio.create_task(self._run_scenario(queue))
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def close(self) -> None:
        self._closed = True
        self._connected = False
        for queue in self._subscribers:
            await queue.put(None)

    def _build_initial_states(self) -> tuple[VehicleState, ...]:
        base = _base_state(scenario=self._scenario)
        if self._scenario == MockVehicleScenario.DISCONNECTED:
            return (
                replace(
                    base,
                    connection_state=VehicleConnectionState.DISCONNECTED,
                    is_plugged_in=False,
                    is_charging=False,
                    state_of_charge_percent=None,
                    electric_range_km=None,
                    data_quality=DataQuality.UNKNOWN,
                ),
            )
        if self._scenario == MockVehicleScenario.STALE_TELEMETRY:
            stale_at = datetime.now(UTC) - timedelta(minutes=20)
            return (
                replace(
                    base,
                    connection_state=VehicleConnectionState.DEGRADED,
                    is_plugged_in=True,
                    is_charging=False,
                    state_of_charge_percent=44.0,
                    electric_range_km=276.0,
                    last_vehicle_update=stale_at,
                    last_provider_update=stale_at,
                    data_quality=DataQuality.STALE,
                    soc_quality=DataQuality.STALE,
                    range_quality=DataQuality.STALE,
                ),
            )
        return (
            replace(
                base,
                connection_state=VehicleConnectionState.CONNECTED,
                is_plugged_in=True,
                is_charging=False,
                state_of_charge_percent=34.0,
                electric_range_km=210.0,
                last_vehicle_update=datetime.now(UTC),
                data_quality=DataQuality.MEASURED,
                soc_quality=DataQuality.MEASURED,
                range_quality=DataQuality.MEASURED,
            ),
        )

    async def _run_scenario(self, queue: asyncio.Queue[VehicleStateChangedEvent | None]) -> None:
        if self._scenario == MockVehicleScenario.DISCONNECTED:
            return
        if self._scenario == MockVehicleScenario.STALE_TELEMETRY:
            return
        if self._scenario == MockVehicleScenario.WEBSOCKET_DISCONNECT:
            await self._emit(queue, self._states["mock-eqe-500"])
            await asyncio.sleep(self._tick_seconds)
            disconnected = replace(
                self._states["mock-eqe-500"],
                connection_state=VehicleConnectionState.RECONNECTING,
                data_quality=DataQuality.UNKNOWN,
            )
            await self._emit(queue, disconnected)
            return
        if self._scenario == MockVehicleScenario.CONNECTED_IDLE:
            await self._emit(queue, self._states["mock-eqe-500"])
            return
        if self._scenario == MockVehicleScenario.TARGET_REACHED:
            reached = replace(
                self._states["mock-eqe-500"],
                state_of_charge_percent=80.0,
                is_charging=False,
                charging_power_kw=0.0,
                electric_range_km=420.0,
                data_quality=DataQuality.MEASURED,
            )
            await self._emit(queue, reached)
            return

        # CHARGING_RAMP: 3.7 -> 7.4 -> 11 kW with rising SoC
        powers = (3.7, 7.4, 11.0)
        socs = (34.0, 38.0, 44.0, 50.0)
        current = self._states["mock-eqe-500"]
        for power, soc in zip(powers, socs, strict=False):
            current = replace(
                current,
                is_charging=True,
                charging_power_kw=power,
                state_of_charge_percent=soc,
                electric_range_km=210.0 + (soc - 34.0) * 5.0,
                last_vehicle_update=datetime.now(UTC),
                last_provider_update=datetime.now(UTC),
                data_quality=DataQuality.MEASURED,
                charging_power_quality=DataQuality.MEASURED,
                soc_quality=DataQuality.MEASURED,
            )
            await self._emit(queue, current)
            await asyncio.sleep(self._tick_seconds)

    async def _emit(self, queue: asyncio.Queue[VehicleStateChangedEvent | None], state: VehicleState) -> None:
        previous = self._states.get(state.vehicle_id)
        self._states[state.vehicle_id] = state
        await queue.put(VehicleStateChangedEvent(state=state, previous_state=previous))
