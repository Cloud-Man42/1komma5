"""Inverter telemetry read port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IInverterTelemetry(Protocol):
    async def get_solar_power_w(self) -> float | None: ...

    async def get_battery_soc_pct(self) -> float | None: ...

    async def get_battery_power_w(self) -> float | None: ...

    async def get_grid_power_w(self) -> float | None: ...
