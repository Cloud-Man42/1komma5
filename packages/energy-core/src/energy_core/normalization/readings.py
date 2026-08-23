"""Normalize raw provider readings into domain-safe values."""

from __future__ import annotations

from datetime import UTC

from energy_core.domain import NormalizedEnergyReading, RawEnergyReading


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def normalize_reading(raw: RawEnergyReading) -> NormalizedEnergyReading:
    recorded_at = raw.recorded_at
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    else:
        recorded_at = recorded_at.astimezone(UTC)

    solar = max(0.0, raw.solar_production_w)
    consumption = max(0.0, raw.consumption_w)
    grid_import = max(0.0, raw.grid_import_w)
    grid_export = max(0.0, raw.grid_export_w)
    battery_soc = _clamp(raw.battery_soc_pct, 0.0, 100.0)

    return NormalizedEnergyReading(
        site_slug=raw.site_slug,
        recorded_at=recorded_at,
        solar_production_w=solar,
        consumption_w=consumption,
        grid_import_w=grid_import,
        grid_export_w=grid_export,
        battery_soc_pct=battery_soc,
        battery_power_w=raw.battery_power_w,
        ev_power_w=raw.ev_power_w,
        battery_charge_w=raw.battery_charge_w,
        battery_discharge_w=raw.battery_discharge_w,
    )
