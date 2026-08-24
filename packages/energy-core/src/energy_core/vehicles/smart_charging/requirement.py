"""Compute vehicle energy need from normalized telemetry."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from energy_core.vehicles.sessions.constants import DEFAULT_BATTERY_CAPACITY_KWH
from energy_core.vehicles.smart_charging.models import VehicleEnergyRequirement


def compute_energy_requirement(
    *,
    current_soc_percent: float | None,
    target_soc_percent: float | None,
    battery_capacity_kwh: float = DEFAULT_BATTERY_CAPACITY_KWH,
) -> VehicleEnergyRequirement:
    if current_soc_percent is None or target_soc_percent is None:
        return VehicleEnergyRequirement(
            current_soc_percent=current_soc_percent,
            target_soc_percent=target_soc_percent,
            required_energy_kwh=None,
            battery_capacity_kwh=battery_capacity_kwh,
            quality="UNAVAILABLE",
        )

    gap_pct = max(0.0, target_soc_percent - current_soc_percent)
    if gap_pct <= 0.05:
        return VehicleEnergyRequirement(
            current_soc_percent=current_soc_percent,
            target_soc_percent=target_soc_percent,
            required_energy_kwh=0.0,
            battery_capacity_kwh=battery_capacity_kwh,
            quality="MEASURED",
        )

    required = gap_pct * battery_capacity_kwh / 100.0
    return VehicleEnergyRequirement(
        current_soc_percent=current_soc_percent,
        target_soc_percent=target_soc_percent,
        required_energy_kwh=required,
        battery_capacity_kwh=battery_capacity_kwh,
        quality="ESTIMATED",
    )


def departure_time_label(departure: datetime | None, timezone: str) -> str | None:
    if departure is None:
        return None
    ts = departure
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(ZoneInfo(timezone)).strftime("%H:%M")


def resolve_vehicle_deadline(
    *,
    departure: datetime | None,
    estimated_complete_at: datetime | None,
    timezone: str,
    now: datetime,
) -> datetime | None:
    del timezone, now
    if departure is not None:
        ts = departure if departure.tzinfo is not None else departure.replace(tzinfo=UTC)
        return ts.astimezone(UTC)
    if estimated_complete_at is not None:
        ts = (
            estimated_complete_at
            if estimated_complete_at.tzinfo is not None
            else estimated_complete_at.replace(tzinfo=UTC)
        )
        return ts.astimezone(UTC)
    return None
