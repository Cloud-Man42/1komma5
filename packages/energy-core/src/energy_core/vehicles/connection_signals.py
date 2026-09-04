"""Resolve effective plug/charge state from Mercedes, Halo, and correlation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS

POWER_CHARGING_THRESHOLD_KW = 0.3


def _age_seconds(timestamp: datetime | None, *, now: datetime | None = None) -> float | None:
    if timestamp is None:
        return None
    current = now or datetime.now(UTC)
    ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
    return max(0.0, (current - ts).total_seconds())


def _trusted_power_kw(
    *,
    is_charging: bool | None,
    charging_power_kw: float | None,
    charging_updated_at: datetime | None = None,
    now: datetime | None = None,
) -> float:
    """Ignore stale positive kW when Mercedes explicitly reports not charging."""
    if is_charging is False:
        ch_age = _age_seconds(charging_updated_at, now=now)
        if ch_age is None or ch_age > STALE_TELEMETRY_SECONDS:
            return 0.0
    return charging_power_kw or 0.0


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


def _resolve_mercedes_charging(latest: VehicleStateLatestModel, *, now: datetime | None = None) -> bool:
    """Derive charging state; stale charging telemetry must not block an active plug-in."""
    current = now or datetime.now(UTC)
    ch_age = _age_seconds(getattr(latest, "charging_updated_at", None), now=current)
    power_kw = _trusted_power_kw(
        is_charging=latest.is_charging,
        charging_power_kw=latest.charging_power_kw,
        charging_updated_at=getattr(latest, "charging_updated_at", None),
        now=current,
    )

    if latest.is_charging is True:
        return True
    if power_kw >= POWER_CHARGING_THRESHOLD_KW:
        return True
    if latest.is_charging is False and ch_age is not None and ch_age <= STALE_TELEMETRY_SECONDS:
        return False
    if latest.is_plugged_in is True and ch_age is not None and ch_age > STALE_TELEMETRY_SECONDS:
        return True
    return bool(latest.is_charging)


def resolve_effective_connection(
    latest: VehicleStateLatestModel | None,
    *,
    halo_vehicle_connected: bool | None = None,
    halo_charger_active: bool | None = None,
    plugged_agreement: bool | None = None,
    now: datetime | None = None,
) -> EffectiveConnection:
    """Self-healing connection state for session lifecycle and display."""
    if latest is None:
        return EffectiveConnection(False, False)

    current = now or datetime.now(UTC)
    power_kw = _trusted_power_kw(
        is_charging=latest.is_charging,
        charging_power_kw=latest.charging_power_kw,
        charging_updated_at=getattr(latest, "charging_updated_at", None),
        now=current,
    )
    mercedes_charging = _resolve_mercedes_charging(latest, now=current)
    mercedes_plugged = infer_plugged_in_from_mercedes(
        is_plugged_in=latest.is_plugged_in,
        is_charging=latest.is_charging,
        charging_power_kw=power_kw,
    )

    if latest.is_plugged_in is True:
        if plugged_agreement is False and not mercedes_charging:
            return EffectiveConnection(False, False)
        return EffectiveConnection(True, mercedes_charging)

    raw_power_kw = latest.charging_power_kw or 0.0
    ch_age = _age_seconds(getattr(latest, "charging_updated_at", None), now=current)
    if (
        latest.is_charging is False
        and raw_power_kw >= POWER_CHARGING_THRESHOLD_KW
        and (ch_age is None or ch_age > STALE_TELEMETRY_SECONDS)
    ):
        return EffectiveConnection(False, False)

    if plugged_agreement is False and not mercedes_charging:
        return EffectiveConnection(False, False)

    if (
        halo_vehicle_connected is False
        and latest.is_plugged_in is not True
        and not mercedes_charging
        and power_kw < POWER_CHARGING_THRESHOLD_KW
    ):
        return EffectiveConnection(False, False)

    if mercedes_plugged is False:
        return EffectiveConnection(False, mercedes_charging)

    if mercedes_plugged is True:
        return EffectiveConnection(True, mercedes_charging)

    if halo_vehicle_connected is True:
        return EffectiveConnection(True, mercedes_charging or bool(halo_charger_active))

    if not mercedes_charging and power_kw < POWER_CHARGING_THRESHOLD_KW:
        return EffectiveConnection(False, False)

    return EffectiveConnection(False, mercedes_charging)
