"""Battery telemetry read port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IBatteryTelemetry(Protocol):
    async def get_soc_pct(self) -> float | None: ...

    async def get_power_w(self) -> float | None: ...

    async def get_capacity_kwh(self) -> float | None: ...
