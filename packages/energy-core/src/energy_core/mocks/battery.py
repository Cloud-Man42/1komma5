"""Vendor-neutral mock battery telemetry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockBattery:
    soc_pct: float | None = 80.0
    power_w: float | None = -1200.0
    capacity_kwh: float | None = 10.0

    async def get_soc_pct(self) -> float | None:
        return self.soc_pct

    async def get_power_w(self) -> float | None:
        return self.power_w

    async def get_capacity_kwh(self) -> float | None:
        return self.capacity_kwh
