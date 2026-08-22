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
) -> tuple[float, float]:
    if grid_import is not None or grid_export is not None:
        return float(grid_import or 0.0), float(grid_export or 0.0)
    if grid_power is None:
        return 0.0, 0.0
    if grid_power >= 0:
        return float(grid_power), 0.0
    return 0.0, float(-grid_power)


def live_overview_to_raw_reading(site_slug: str, data: dict[str, Any]) -> RawEnergyReading:
    """Convert a /v3/systems/{id}/live-overview response to RawEnergyReading."""
    from onekommafive.models.live import LiveOverview

    overview = LiveOverview.from_dict(data)
    grid_import, grid_export = _grid_import_export(
        grid_import=overview.grid_consumption_power,
        grid_export=overview.grid_feed_in_power,
        grid_power=overview.grid_power,
    )
    consumption = overview.consumption_power
    if consumption is None:
        consumption = overview.household_power

    battery_power = float(overview.battery_power or 0.0)
    battery_charge_w = max(0.0, battery_power)
    battery_discharge_w = abs(min(0.0, battery_power))

    from energy_core.heartbeat.live_overview import extract_pv_power_w, parse_live_overview

    parsed = parse_live_overview(data)
    ev_power = parsed.get("ev_actual_power_w")
    pv_power = extract_pv_power_w(data)

    return RawEnergyReading(
        site_slug=site_slug,
        recorded_at=_parse_timestamp(overview.timestamp),
        solar_production_w=float(pv_power if pv_power is not None else overview.pv_power or 0.0),
        consumption_w=float(consumption or 0.0),
        grid_import_w=grid_import,
        grid_export_w=grid_export,
        battery_soc_pct=float(overview.battery_soc or 0.0),
        battery_power_w=battery_power,
        ev_power_w=ev_power,
        battery_charge_w=battery_charge_w,
        battery_discharge_w=battery_discharge_w,
    )
