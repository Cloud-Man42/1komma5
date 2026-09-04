"""Reject Mercedes sleeping/placeholder telemetry before it overwrites good readings."""

from __future__ import annotations

from energy_core.vehicles.abstractions.models import VehicleState


def has_plausible_vehicle_telemetry(state: VehicleState) -> bool:
    """True when Mercedes values look like a real vehicle snapshot, not sleep placeholders."""
    soc = state.state_of_charge_percent
    range_km = state.electric_range_km
    power_kw = state.charging_power_kw

    if soc is not None and 0 < soc <= 100:
        return True
    if range_km is not None and range_km > 0:
        return True
    if power_kw is not None and power_kw > 0:
        return True
    if state.is_charging is True:
        return True
    if state.is_plugged_in is True:
        return True
    if state.latitude is not None and state.longitude is not None:
        return True
    return False


def sanitize_vehicle_state(state: VehicleState) -> VehicleState:
    """Drop implausible placeholder fields so LKG merge keeps the last good values."""
    from dataclasses import replace

    power_kw = state.charging_power_kw
    if power_kw == 0 and state.is_charging is False:
        power_kw = 0.0
    elif power_kw == 0:
        power_kw = None

    return replace(
        state,
        state_of_charge_percent=None if _is_sleep_placeholder_soc(state) else state.state_of_charge_percent,
        electric_range_km=None if _is_sleep_placeholder_range(state) else state.electric_range_km,
        charging_power_kw=power_kw,
    )


def _is_sleep_placeholder_soc(state: VehicleState) -> bool:
    soc = state.state_of_charge_percent
    if soc is None:
        return False
    if soc > 0:
        return False
    range_km = state.electric_range_km
    return range_km is None or range_km <= 0


def _is_sleep_placeholder_range(state: VehicleState) -> bool:
    range_km = state.electric_range_km
    if range_km is None or range_km > 0:
        return False
    soc = state.state_of_charge_percent
    return soc is None or soc <= 0
