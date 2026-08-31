"""Map HeartBeat live-overview payloads to domain energy readings."""

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


def _grid_import_export(
    *,
    grid_import: float | None,
    grid_export: float | None,
    grid_power: float | None,
) -> tuple[float | None, float | None, frozenset[str]]:
    present: set[str] = set()
    if grid_import is not None:
        present.add("grid_import_w")
        import_w = float(grid_import)
    elif grid_power is not None and grid_power >= 0:
        present.update({"grid_import_w"})
        import_w = float(grid_power)
    else:
        import_w = None

    if grid_export is not None:
        present.add("grid_export_w")
        export_w = float(grid_export)
    elif grid_power is not None and grid_power < 0:
        present.update({"grid_export_w"})
        export_w = float(-grid_power)
    else:
        export_w = None

    if import_w is None and export_w is None and grid_power is None:
        return 0.0, 0.0, frozenset()
    return float(import_w or 0.0), float(export_w or 0.0), frozenset(present)


def live_overview_to_raw_reading(site_slug: str, data: dict[str, Any]) -> RawEnergyReading:
    """Convert a /v3/systems/{id}/live-overview response to RawEnergyReading."""
    from onekommafive.models.live import LiveOverview

    overview = LiveOverview.from_dict(data)
    grid_import, grid_export, grid_present = _grid_import_export(
        grid_import=overview.grid_consumption_power,
        grid_export=overview.grid_feed_in_power,
        grid_power=overview.grid_power,
    )
    consumption = overview.consumption_power
    if consumption is None:
        consumption = overview.household_power

    present: set[str] = set(grid_present)
    battery_power: float | None = None
    if overview.battery_power is not None:
        battery_power = float(overview.battery_power)
        present.add("battery_power_w")

    battery_charge_w = max(0.0, battery_power) if battery_power is not None else None
    battery_discharge_w = abs(min(0.0, battery_power)) if battery_power is not None else None

    from energy_core.heartbeat.live_overview import extract_pv_power_w, parse_live_overview

    parsed = parse_live_overview(data)
    ev_power = parsed.get("ev_actual_power_w")
    pv_power = extract_pv_power_w(data)

    solar_w = 0.0
    if pv_power is not None:
        solar_w = float(pv_power)
        present.add("solar_production_w")
    elif overview.pv_power is not None:
        solar_w = float(overview.pv_power)
        present.add("solar_production_w")

    consumption_w = 0.0
    if consumption is not None:
        consumption_w = float(consumption)
        present.add("consumption_w")

    battery_soc = 0.0
    if overview.battery_soc is not None:
        battery_soc = float(overview.battery_soc)
        present.add("battery_soc_pct")

    return RawEnergyReading(
        site_slug=site_slug,
        recorded_at=_parse_timestamp(overview.timestamp),
        solar_production_w=solar_w,
        consumption_w=consumption_w,
        grid_import_w=grid_import,
        grid_export_w=grid_export,
        battery_soc_pct=battery_soc,
        battery_power_w=float(battery_power or 0.0),
        ev_power_w=ev_power,
        battery_charge_w=battery_charge_w,
        battery_discharge_w=battery_discharge_w,
        present_fields=frozenset(present),
    )
