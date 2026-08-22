"""Manual override window for EV charger bridge control."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.charging.models import ChargingDecision
from energy_core.charging.power_to_current import power_to_current_a

ALLOWED_OVERRIDE_HOURS = frozenset({4, 8, 12, 24})


@dataclass(frozen=True, slots=True)
class BridgeChargerConfig:
    max_current_a: float = 16.0
    min_current_a: float = 6.0
    phases: int = 3
    nominal_voltage_v: float = 230.0
    max_power_w: float | None = None


def override_active(override_until: datetime | None, *, now: datetime | None = None) -> bool:
    if override_until is None:
        return False
    current = now or datetime.now(UTC)
    until = override_until if override_until.tzinfo else override_until.replace(tzinfo=UTC)
    return until > current


def override_until_from_hours(hours: int, *, now: datetime | None = None) -> datetime:
    if hours not in ALLOWED_OVERRIDE_HOURS:
        raise ValueError(f"Unsupported override duration: {hours}")
    current = now or datetime.now(UTC)
    return current + timedelta(hours=hours)


def _max_allowed_power(config: BridgeChargerConfig) -> float:
    if config.max_power_w is not None:
        return config.max_power_w
    if config.phases >= 3:
        return config.max_current_a * math.sqrt(3) * config.nominal_voltage_v
    return config.max_current_a * config.nominal_voltage_v


def override_decision(*, config: BridgeChargerConfig) -> ChargingDecision:
    power = _max_allowed_power(config)
    current = power_to_current_a(
        power,
        phases=config.phases,
        nominal_voltage_v=config.nominal_voltage_v,
        min_current_a=config.min_current_a,
        max_current_a=config.max_current_a,
        max_power_w=config.max_power_w,
    )
    return ChargingDecision(
        requested_current_a=current,
        applied_current_a=current,
        requested_power_w=power,
        action="set_current" if current else "pause",
        reason="manual_override",
        policy_mode="override",
    )
