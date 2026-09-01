"""Adaptive polling intervals for Mercedes REST refresh."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum

from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


class VehicleActivityMode(StrEnum):
    DRIVING = "DRIVING"
    CHARGING = "CHARGING"
    POSITION_RECOVERY = "POSITION_RECOVERY"
    RECENTLY_PARKED = "RECENTLY_PARKED"
    STALE_RECOVERY = "STALE_RECOVERY"
    SLEEPING = "SLEEPING"
    NIGHT_INACTIVE = "NIGHT_INACTIVE"
    DEFAULT = "DEFAULT"


@dataclass(frozen=True, slots=True)
class PollingDecision:
    mode: VehicleActivityMode
    interval_seconds: int


class AdaptivePollingPlanner:
    """Choose REST polling interval based on vehicle/integration activity."""

    INTERVALS = {
        VehicleActivityMode.DRIVING: (30, 60),
        VehicleActivityMode.CHARGING: (30, 60),
        VehicleActivityMode.POSITION_RECOVERY: (30, 30),
        VehicleActivityMode.RECENTLY_PARKED: (120, 120),
        VehicleActivityMode.STALE_RECOVERY: (60, 120),
        VehicleActivityMode.SLEEPING: (600, 900),
        VehicleActivityMode.NIGHT_INACTIVE: (900, 1800),
        VehicleActivityMode.DEFAULT: (300, 300),
    }

    def decide(
        self,
        *,
        is_charging: bool | None,
        is_plugged_in: bool | None,
        last_vehicle_update: datetime | None,
        vehicle_data_age_seconds: float | None = None,
        charging_power_kw: float | None = None,
        missing_gps: bool = False,
        away_from_home: bool = False,
        now: datetime | None = None,
    ) -> PollingDecision:
        current = now or datetime.now(UTC)
        is_charging, is_plugged_in = _infer_charging_signals(
            is_charging=is_charging,
            is_plugged_in=is_plugged_in,
            charging_power_kw=charging_power_kw,
        )
        age = vehicle_data_age_seconds
        if age is None and last_vehicle_update is not None:
            ts = last_vehicle_update if last_vehicle_update.tzinfo else last_vehicle_update.replace(tzinfo=UTC)
            age = max(0.0, (current - ts).total_seconds())

        if missing_gps and away_from_home and (is_charging is True or is_plugged_in is True):
            return PollingDecision(
                VehicleActivityMode.POSITION_RECOVERY,
                self.INTERVALS[VehicleActivityMode.POSITION_RECOVERY][0],
            )

        if is_charging is True or is_plugged_in is True:
            return PollingDecision(VehicleActivityMode.CHARGING, self._pick(self.INTERVALS[VehicleActivityMode.CHARGING]))

        if age is not None and age <= 180:
            return PollingDecision(VehicleActivityMode.RECENTLY_PARKED, self.INTERVALS[VehicleActivityMode.RECENTLY_PARKED][0])

        if age is not None and age > STALE_TELEMETRY_SECONDS:
            if _is_night_inactive(current):
                low, high = self.INTERVALS[VehicleActivityMode.NIGHT_INACTIVE]
                return PollingDecision(VehicleActivityMode.NIGHT_INACTIVE, (low + high) // 2)
            low, high = self.INTERVALS[VehicleActivityMode.STALE_RECOVERY]
            return PollingDecision(VehicleActivityMode.STALE_RECOVERY, (low + high) // 2)

        return PollingDecision(VehicleActivityMode.DEFAULT, self.INTERVALS[VehicleActivityMode.DEFAULT][0])

    @staticmethod
    def _pick(bounds: tuple[int, int]) -> int:
        low, high = bounds
        if low == high:
            return low
        return (low + high) // 2


def _is_night_inactive(now: datetime) -> bool:
    local_hour = now.hour
    return local_hour >= 23 or local_hour < 6


def _infer_charging_signals(
    *,
    is_charging: bool | None,
    is_plugged_in: bool | None,
    charging_power_kw: float | None,
) -> tuple[bool | None, bool | None]:
    """Keep charging mode when Mercedes drops plug flags but power is still flowing."""
    if is_charging is None and charging_power_kw is not None and charging_power_kw >= 0.3:
        is_charging = True
    if is_plugged_in is None and is_charging is True:
        is_plugged_in = True
    return is_charging, is_plugged_in
