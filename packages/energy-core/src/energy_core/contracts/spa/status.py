"""Vendor-neutral spa status surface."""

from __future__ import annotations

from typing import Any, Protocol


class SpaStatus(Protocol):
    connected: bool
    temperature_c: float | None
    setpoint_c: float | None
    filter_status: str | None
    filter_duration: int | None
    filter_frequency: float | None
    errors: tuple[str, ...]

    @property
    def filter_cycle_active(self) -> bool: ...

    @property
    def heater_active(self) -> bool: ...

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> SpaStatus: ...
