"""Normalized energy state for charging policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class EnergyState:
    timestamp: datetime
    electricity_price_eur_kwh: float | None = None
    price_forecast: tuple[tuple[datetime, float], ...] = ()
    import_price_sek_kwh: float | None = None
    import_price_forecast: tuple[tuple[datetime, float], ...] = ()
    pv_power_w: float | None = None
    grid_power_w: float | None = None
    grid_import_w: float | None = None
    grid_export_w: float | None = None
    home_consumption_w: float | None = None
    battery_power_w: float | None = None
    battery_charge_power_w: float | None = None
    battery_discharge_power_w: float | None = None
    battery_soc: float | None = None
    phase_current_l1_a: float | None = None
    phase_current_l2_a: float | None = None
    phase_current_l3_a: float | None = None
    ev_actual_power_w: float | None = None
    ev_target_power_w: float | None = None
    heartbeat_charging_mode: str | None = None
    heartbeat_smart_charge_active: bool = False
    ev_charge_from_grid_recommended: bool = False
    departure_time: str | None = None
    deadline_at: datetime | None = None
    target_soc: float | None = None
    ev_soc: float | None = None
    vehicle_required_energy_kwh: float | None = None
    vehicle_energy_quality: str | None = None
    vehicle_linked: bool = False
    vehicle_display_name: str | None = None
    data_age_seconds: float = 0.0
    raw_field_hints: tuple[str, ...] = ()
    stale: bool = False

    def with_age(self, now: datetime | None = None) -> EnergyState:
        now = now or datetime.now(UTC)
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age = max(0.0, (now - ts).total_seconds())
        return replace(self, data_age_seconds=age)
