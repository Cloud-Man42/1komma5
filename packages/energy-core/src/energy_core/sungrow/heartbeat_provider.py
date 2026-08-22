"""Map Heartbeat live-overview payloads to SungrowTelemetrySnapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.heartbeat.live_overview import parse_live_overview
from energy_core.sungrow.types import SungrowTelemetrySnapshot


def _non_negative(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, float(value))


def _grid_import_export(
    *,
    grid_import: float | None,
    grid_export: float | None,
    grid_power: float | None,
) -> tuple[float | None, float | None]:
    if grid_import is not None or grid_export is not None:
        return _non_negative(grid_import), _non_negative(grid_export)
    if grid_power is None:
        return None, None
    if grid_power >= 0:
        return float(grid_power), 0.0
    return 0.0, float(-grid_power)


def map_heartbeat_to_sungrow(
    data: dict[str, Any],
    *,
    max_age_seconds: float = 60.0,
    now: datetime | None = None,
) -> SungrowTelemetrySnapshot:
    """Convert Heartbeat live-overview JSON to canonical Sungrow snapshot."""
    parsed = parse_live_overview(data)
    now = now or datetime.now(UTC)
    recorded_at = parsed["timestamp"]
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    age = max(0.0, (now - recorded_at).total_seconds())

    grid_import, grid_export = _grid_import_export(
        grid_import=parsed.get("grid_import_w"),
        grid_export=parsed.get("grid_export_w"),
        grid_power=parsed.get("grid_power_w"),
    )

    status = data.get("status")
    inverter_status = str(status) if status is not None else None

    return SungrowTelemetrySnapshot(
        recorded_at=recorded_at,
        pv_power_w=_non_negative(parsed.get("pv_power_w")),
        pv_energy_today_kwh=None,
        load_power_w=_non_negative(parsed.get("home_consumption_w")),
        grid_import_w=grid_import,
        grid_export_w=grid_export,
        battery_charge_w=_non_negative(parsed.get("battery_charge_power_w")),
        battery_discharge_w=_non_negative(parsed.get("battery_discharge_power_w")),
        battery_soc_pct=parsed.get("battery_soc"),
        inverter_status=inverter_status,
        data_age_seconds=age,
        fresh=age <= max_age_seconds,
        source="heartbeat",
    )
