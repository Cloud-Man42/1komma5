"""Vendor-neutral mock spa control."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockSpa:
    temperature_c: float = 38.0
    power_w: float = 1500.0
    heating: bool = True

    async def get_temperature_c(self) -> float | None:
        return self.temperature_c

    async def set_temperature_c(self, temperature: float) -> None:
        self.temperature_c = temperature

    async def get_power_w(self) -> float | None:
        return self.power_w if self.heating else 0.0

    async def is_heating(self) -> bool:
        return self.heating
