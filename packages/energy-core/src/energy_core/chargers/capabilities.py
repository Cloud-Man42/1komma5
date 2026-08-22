"""Charger capability model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChargerCapabilities:
    min_current_a: float
    max_current_a: float
    phases: int | None
    supports_current_control: bool
    supports_remote_start_stop: bool
    supports_power_reading: bool
    supports_dynamic_phases: bool
