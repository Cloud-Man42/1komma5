"""Resolve effective plug/charge state from Mercedes, Halo, and correlation."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.db.models import VehicleStateLatestModel

POWER_CHARGING_THRESHOLD_KW = 0.3


@dataclass(frozen=True, slots=True)
class EffectiveConnection:
    is_plugged_in: bool
    is_charging: bool


def infer_plugged_in_from_mercedes(
    *,
    is_plugged_in: bool | None,
    is_charging: bool | None,
    charging_power_kw: float | None,
    charging_status_label: str | None = None,
) -> bool | None:
    """Turn ambiguous Mercedes signals into a definitive plug state when possible."""
    if is_plugged_in is False:
        return False
    if is_plugged_in is True:
        return True
    if is_charging is True:
        return True

    power_kw = charging_power_kw or 0.0
    if power_kw >= POWER_CHARGING_THRESHOLD_KW:
        return True

    if is_charging is False and power_kw < POWER_CHARGING_THRESHOLD_KW:
        if charging_status_label in {None, "not_charging", "unknown"}:
            return False

    return None


def resolve_effective_connection(
    latest: VehicleStateLatestModel | None,
    *,
    halo_vehicle_connected: bool | None = None,
    halo_charger_active: bool | None = None,
    plugged_agreement: bool | None = None,
) -> EffectiveConnection:
    """Self-healing connection state for session lifecycle and display."""
    if latest is None:
        return EffectiveConnection(False, False)

    power_kw = latest.charging_power_kw
    mercedes_charging = latest.is_charging is True or (power_kw or 0.0) >= POWER_CHARGING_THRESHOLD_KW
    mercedes_plugged = infer_plugged_in_from_mercedes(
        is_plugged_in=latest.is_plugged_in,
        is_charging=latest.is_charging,
        charging_power_kw=power_kw,
    )

    if plugged_agreement is False and not mercedes_charging:
        return EffectiveConnection(False, False)

    if halo_vehicle_connected is False and not mercedes_charging and (power_kw or 0.0) < POWER_CHARGING_THRESHOLD_KW:
        return EffectiveConnection(False, False)

    if mercedes_plugged is False:
        return EffectiveConnection(False, mercedes_charging)

    if mercedes_plugged is True:
        return EffectiveConnection(True, mercedes_charging)

    if halo_vehicle_connected is True:
        return EffectiveConnection(True, mercedes_charging or bool(halo_charger_active))

    if not mercedes_charging and (power_kw or 0.0) < POWER_CHARGING_THRESHOLD_KW:
        return EffectiveConnection(False, False)

    return EffectiveConnection(False, mercedes_charging)
