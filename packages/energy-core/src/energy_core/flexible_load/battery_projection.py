"""Forward battery SoC projection for flexible load planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class BatteryProjectionConfig:
    reserve_soc_pct: float = 25.0
    max_charge_power_w: float = 5000.0
    max_discharge_power_w: float = 5000.0
    battery_capacity_kwh: float = 10.0
    interval_hours: float = 0.25


class BatterySoCProjector:
    """Walk battery SoC forward using projected surplus/deficit per block."""

    def project(
        self,
        timestamps: tuple[datetime, ...],
        *,
        initial_soc_pct: float,
        surplus_w_by_ts: dict[datetime, float],
        config: BatteryProjectionConfig,
    ) -> dict[datetime, float]:
        if not timestamps:
            return {}

        soc_pct = max(config.reserve_soc_pct, min(100.0, initial_soc_pct))
        capacity_wh = config.battery_capacity_kwh * 1000.0
        result: dict[datetime, float] = {}

        for ts in timestamps:
            result[ts] = soc_pct
            surplus_w = surplus_w_by_ts.get(ts, 0.0)
            if surplus_w > 0:
                charge_w = min(surplus_w, config.max_charge_power_w)
                delta_wh = charge_w * config.interval_hours
                soc_pct = min(100.0, soc_pct + (delta_wh / capacity_wh) * 100.0)
            elif surplus_w < 0:
                discharge_w = min(abs(surplus_w), config.max_discharge_power_w)
                delta_wh = discharge_w * config.interval_hours
                soc_pct = max(config.reserve_soc_pct, soc_pct - (delta_wh / capacity_wh) * 100.0)

        return result
