"""Vendor-neutral mock inverter telemetry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockInverter:
    solar_power_w: float | None = 2500.0
    battery_soc_pct: float | None = 75.0
    battery_power_w: float | None = -500.0
    grid_power_w: float | None = 200.0

    async def get_solar_power_w(self) -> float | None:
        return self.solar_power_w

    async def get_battery_soc_pct(self) -> float | None:
        return self.battery_soc_pct

    async def get_battery_power_w(self) -> float | None:
        return self.battery_power_w

    async def get_grid_power_w(self) -> float | None:
        return self.grid_power_w
