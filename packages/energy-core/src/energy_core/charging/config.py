"""Smart charging configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ChargingConfig:
    max_current_a: float = 16.0
    min_current_a: float = 6.0
    phases: int = 3
    nominal_voltage_v: float = 230.0
    max_power_w: float | None = None
    max_grid_import_w: float | None = None
    main_fuse_a: float | None = None
    safety_margin_a: float = 2.0
    expensive_price_eur_kwh: float = 0.35
    solar_start_threshold_w: float = 1000.0
    solar_stop_threshold_w: float = 600.0
    solar_start_delay_seconds: float = 15.0
    solar_stop_delay_seconds: float = 60.0
    battery_low_soc_threshold: float = 20.0
    battery_charge_power_threshold_w: float = 1500.0
    smart_charge_hours: float = 4.0
    timezone: str = "Europe/Stockholm"
    deadline_at: datetime | None = None
    departure_time: str | None = None
    start_delay_seconds: float = 120.0
    stop_delay_seconds: float = 300.0
    minimum_run_time_seconds: float = 300.0
    minimum_off_time_seconds: float = 300.0
    temporary_grid_import_allowance_w: float = 800.0
    temporary_grid_import_seconds: float = 180.0
    grid_deadband_w: float = 300.0
    minimum_current_change_interval_seconds: float = 30.0
    max_current_increase_per_step_a: float = 1.0
    max_current_decrease_per_step_a: float = 2.0
    max_automatic_starts_per_hour: int = 4
