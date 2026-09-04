"""Adaptive polling intervals for Mercedes REST refresh."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from enum import StrEnum

from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS


class VehicleActivityMode(StrEnum):
    DRIVING = "DRIVING"
    CHARGING = "CHARGING"
    PLUGGED = "PLUGGED"
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
        VehicleActivityMode.DRIVING: (60, 120),
        VehicleActivityMode.CHARGING: (90, 120),
        VehicleActivityMode.PLUGGED: (180, 300),
        VehicleActivityMode.POSITION_RECOVERY: (60, 90),
        VehicleActivityMode.RECENTLY_PARKED: (180, 180),
        VehicleActivityMode.STALE_RECOVERY: (180, 300),
        VehicleActivityMode.SLEEPING: (600, 900),
        VehicleActivityMode.NIGHT_INACTIVE: (900, 1800),
        VehicleActivityMode.DEFAULT: (300, 600),
    }

    def decide(
        self,
        *,
        is_charging: bool | None,
        is_plugged_in: bool | None,
        last_vehicle_update: datetime | None,
        vehicle_data_age_seconds: float | None = None,
        soc_updated_at: datetime | None = None,
        charging_power_kw: float | None = None,
        charging_updated_at: datetime | None = None,
        missing_gps: bool = False,
        away_from_home: bool = False,
        now: datetime | None = None,
    ) -> PollingDecision:
        current = now or datetime.now(UTC)
        is_charging, is_plugged_in = _infer_charging_signals(
            is_charging=is_charging,
            is_plugged_in=is_plugged_in,
            charging_power_kw=charging_power_kw,
            charging_updated_at=charging_updated_at,
            now=current,
        )
        age = vehicle_data_age_seconds
        if age is None and last_vehicle_update is not None:
            ts = last_vehicle_update if last_vehicle_update.tzinfo else last_vehicle_update.replace(tzinfo=UTC)
            age = max(0.0, (current - ts).total_seconds())
        if soc_updated_at is not None:
            soc_ts = soc_updated_at if soc_updated_at.tzinfo else soc_updated_at.replace(tzinfo=UTC)
            soc_age = max(0.0, (current - soc_ts).total_seconds())
            age = max(age or 0.0, soc_age)

        if missing_gps and away_from_home and (is_charging is True or is_plugged_in is True):
            return PollingDecision(
                VehicleActivityMode.POSITION_RECOVERY,
                self.INTERVALS[VehicleActivityMode.POSITION_RECOVERY][0],
            )

        if is_charging is True:
            return PollingDecision(VehicleActivityMode.CHARGING, self._pick(self.INTERVALS[VehicleActivityMode.CHARGING]))
        if is_plugged_in is True:
            return PollingDecision(VehicleActivityMode.PLUGGED, self._pick(self.INTERVALS[VehicleActivityMode.PLUGGED]))

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
    charging_updated_at: datetime | None = None,
    now: datetime | None = None,
) -> tuple[bool | None, bool | None]:
    """Infer charging only from fresh positive kW; avoid aggressive polling on stale power."""
    current = now or datetime.now(UTC)
    ch_age: float | None = None
    if charging_updated_at is not None:
        ts = charging_updated_at if charging_updated_at.tzinfo else charging_updated_at.replace(tzinfo=UTC)
        ch_age = max(0.0, (current - ts).total_seconds())
    power_fresh = ch_age is not None and ch_age <= STALE_TELEMETRY_SECONDS
    if is_charging is None and power_fresh and charging_power_kw is not None and charging_power_kw >= 0.3:
        is_charging = True
    if is_plugged_in is None and is_charging is True:
        is_plugged_in = True
    return is_charging, is_plugged_in
