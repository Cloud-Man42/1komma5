"""Integrate consecutive power readings into kWh segments."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from typing import Any

MAX_INTERVAL_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class EnergySegment:
    started_at: datetime
    hours: float
    solar_kwh: float
    consumption_kwh: float
    import_kwh: float
    export_kwh: float
    battery_charged_kwh: float = 0.0
    battery_discharged_kwh: float = 0.0


@dataclass(frozen=True, slots=True)
class SiteEnergyTotals:
    solar_kwh: float = 0.0
    consumption_kwh: float = 0.0
    import_kwh: float = 0.0
    export_kwh: float = 0.0
    battery_charged_kwh: float = 0.0
    battery_discharged_kwh: float = 0.0


def _ensure_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp


def _positive_w(value: float | None) -> float:
    return max(0.0, float(value or 0.0))


def _battery_watts(reading: Any) -> tuple[float, float]:
    charge_w = reading.battery_charge_w
    discharge_w = reading.battery_discharge_w
    battery_power_w = getattr(reading, "battery_power_w", None)
    if charge_w is None and battery_power_w is not None:
        charge_w = max(0.0, float(battery_power_w))
    if discharge_w is None and battery_power_w is not None:
        discharge_w = max(0.0, -float(battery_power_w))
    return _positive_w(charge_w), _positive_w(discharge_w)


def iter_energy_segments(
    readings: Sequence[Any],
    *,
    max_interval_seconds: float = MAX_INTERVAL_SECONDS,
    include_battery: bool = False,
) -> Iterator[EnergySegment]:
    """Integrate consecutive readings using left-endpoint power and a capped interval."""
    for previous, current in pairwise(readings):
        started_at = _ensure_utc(previous.recorded_at)
        ended_at = _ensure_utc(current.recorded_at)
        seconds = (ended_at - started_at).total_seconds()
        if seconds <= 0 or seconds > max_interval_seconds:
            continue
        hours = seconds / 3600.0
        solar_kwh = _positive_w(previous.solar_production_w) * hours / 1000.0
        consumption_kwh = _positive_w(previous.consumption_w) * hours / 1000.0
        import_kwh = _positive_w(previous.grid_import_w) * hours / 1000.0
        export_kwh = _positive_w(previous.grid_export_w) * hours / 1000.0
        battery_charged_kwh = battery_discharged_kwh = 0.0
        if include_battery:
            charge_w, discharge_w = _battery_watts(previous)
            battery_charged_kwh = charge_w * hours / 1000.0
            battery_discharged_kwh = discharge_w * hours / 1000.0
        yield EnergySegment(
            started_at=started_at,
            hours=hours,
            solar_kwh=solar_kwh,
            consumption_kwh=consumption_kwh,
            import_kwh=import_kwh,
            export_kwh=export_kwh,
            battery_charged_kwh=battery_charged_kwh,
            battery_discharged_kwh=battery_discharged_kwh,
        )


def integrate_site_energy(
    readings: Sequence[Any],
    *,
    max_interval_seconds: float = MAX_INTERVAL_SECONDS,
    include_battery: bool = False,
) -> SiteEnergyTotals:
    """Sum kWh across all valid reading intervals."""
    solar_kwh = consumption_kwh = import_kwh = export_kwh = 0.0
    battery_charged_kwh = battery_discharged_kwh = 0.0
    for segment in iter_energy_segments(
        readings,
        max_interval_seconds=max_interval_seconds,
        include_battery=include_battery,
    ):
        solar_kwh += segment.solar_kwh
        consumption_kwh += segment.consumption_kwh
        import_kwh += segment.import_kwh
        export_kwh += segment.export_kwh
        battery_charged_kwh += segment.battery_charged_kwh
        battery_discharged_kwh += segment.battery_discharged_kwh
    return SiteEnergyTotals(
        solar_kwh=solar_kwh,
        consumption_kwh=consumption_kwh,
        import_kwh=import_kwh,
        export_kwh=export_kwh,
        battery_charged_kwh=battery_charged_kwh,
        battery_discharged_kwh=battery_discharged_kwh,
    )
