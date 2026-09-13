"""Map GridX /systems/{id}/live payloads to domain energy readings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.domain import RawEnergyReading


def _parse_timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(UTC)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _battery_block(data: dict[str, Any]) -> dict[str, Any]:
    battery = data.get("battery")
    if isinstance(battery, dict):
        return battery
    batteries = data.get("batteries")
    if isinstance(batteries, list) and batteries:
        first = batteries[0]
        return first if isinstance(first, dict) else {}
    return {}


def gridx_live_to_raw_reading(site_slug: str, data: dict[str, Any]) -> RawEnergyReading:
    """Convert GridX GET /systems/{id}/live JSON to RawEnergyReading."""
    present: set[str] = set()

    grid = data.get("grid")
    grid_power = float(grid) if isinstance(grid, (int, float)) else None

    grid_import_w = 0.0
    grid_export_w = 0.0
    if grid_power is not None:
        if grid_power >= 0:
            grid_import_w = float(grid_power)
            present.add("grid_import_w")
        else:
            grid_export_w = float(-grid_power)
            present.add("grid_export_w")

    pv = data.get("photovoltaic")
    if pv is None:
        pv = data.get("production")
    solar_w = 0.0
    if isinstance(pv, (int, float)):
        solar_w = float(pv)
        present.add("solar_production_w")

    consumption = data.get("consumption")
    if consumption is None:
        consumption = data.get("totalConsumption")
    consumption_w = 0.0
    if isinstance(consumption, (int, float)):
        consumption_w = float(consumption)
        present.add("consumption_w")

    battery = _battery_block(data)
    soc_raw = battery.get("stateOfCharge")
    battery_soc = 0.0
    if isinstance(soc_raw, (int, float)):
        battery_soc = float(soc_raw) * 100.0 if soc_raw <= 1.0 else float(soc_raw)
        present.add("battery_soc_pct")
    power = battery.get("power")
    battery_power_w = None
    if isinstance(power, (int, float)):
        # GridX: positive = discharging, negative = charging.
        # EMIC: positive = charging, negative = discharging (same as 1Komma5 Heartbeat).
        battery_power_w = -float(power)
        present.add("battery_power_w")

    return RawEnergyReading(
        site_slug=site_slug,
        recorded_at=_parse_timestamp(data.get("measuredAt") if isinstance(data.get("measuredAt"), str) else None),
        solar_production_w=solar_w,
        consumption_w=consumption_w,
        grid_import_w=grid_import_w,
        grid_export_w=grid_export_w,
        battery_soc_pct=battery_soc,
        battery_power_w=battery_power_w or 0.0,
        present_fields=frozenset(present),
    )
