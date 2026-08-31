"""Adaptive polling intervals for Mercedes REST refresh."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum

from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


class VehicleActivityMode(StrEnum):
    DRIVING = "DRIVING"
    CHARGING = "CHARGING"
    RECENTLY_PARKED = "RECENTLY_PARKED"
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
        VehicleActivityMode.RECENTLY_PARKED: (120, 120),
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
        now: datetime | None = None,
    ) -> PollingDecision:
        current = now or datetime.now(UTC)
        age = vehicle_data_age_seconds
        if age is None and last_vehicle_update is not None:
            ts = last_vehicle_update if last_vehicle_update.tzinfo else last_vehicle_update.replace(tzinfo=UTC)
            age = max(0.0, (current - ts).total_seconds())

        if is_charging or is_plugged_in:
            return PollingDecision(VehicleActivityMode.CHARGING, self._pick(self.INTERVALS[VehicleActivityMode.CHARGING]))

        if age is not None and age <= 180:
            return PollingDecision(VehicleActivityMode.RECENTLY_PARKED, self.INTERVALS[VehicleActivityMode.RECENTLY_PARKED][0])

        if _is_night_inactive(current) and age is not None and age > STALE_TELEMETRY_SECONDS:
            low, high = self.INTERVALS[VehicleActivityMode.NIGHT_INACTIVE]
            return PollingDecision(VehicleActivityMode.NIGHT_INACTIVE, (low + high) // 2)

        if age is not None and age > STALE_TELEMETRY_SECONDS:
            low, high = self.INTERVALS[VehicleActivityMode.SLEEPING]
            return PollingDecision(VehicleActivityMode.SLEEPING, (low + high) // 2)

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
