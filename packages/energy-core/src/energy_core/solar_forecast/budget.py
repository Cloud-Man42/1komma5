"""Solar energy budget calculation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.historical import aggregate_buckets_from_readings
from energy_core.solar_forecast.types import SolarEnergyBudget, SolarForecast


@dataclass(frozen=True, slots=True)
class ConsumptionForecast:
    expected_kwh: float
    source: str = "historical"


class ConsumptionForecastProvider:
    """Historical time-of-day / seasonal consumption profile."""

    def forecast_remaining_today(
        self,
        readings: list[tuple[datetime, float, float]],
        *,
        timezone: str,
        now: datetime,
    ) -> ConsumptionForecast | None:
        if len(readings) < 48:
            return None

        tz = ZoneInfo(timezone)
        local_now = now.astimezone(tz)
        current_hour = local_now.hour
        current_month = local_now.month

        buckets = aggregate_buckets_from_readings(readings)
        if not buckets:
            return None

        # Build hour-of-day profile for same month (or all if sparse)
        hour_consumption: dict[int, list[float]] = {}
        for b in buckets:
            local = b.bucket_start.astimezone(tz)
            if local.month == current_month or len(buckets) < 200:
                from energy_core.solar_forecast.historical import actual_energy_kwh

                hour_consumption.setdefault(local.hour, []).append(actual_energy_kwh(b.avg_consumption_w))

        if not hour_consumption:
            return None

        profile = {h: mean(vals) for h, vals in hour_consumption.items()}
        remaining_hours = list(range(current_hour, 24))
        expected = sum(profile.get(h, 0.0) for h in remaining_hours)
        if expected <= 0:
            return None
        return ConsumptionForecast(expected_kwh=expected, source="historical")


class SolarEnergyBudgetService:
    def compute(
        self,
        forecast: SolarForecast,
        *,
        ev_required_kwh: float | None = None,
        battery_soc_pct: float | None = None,
        battery_capacity_kwh: float | None = None,
        consumption_forecast: ConsumptionForecast | None = None,
    ) -> SolarEnergyBudget:
        solar = forecast.remaining_today_kwh
        house = consumption_forecast.expected_kwh if consumption_forecast else None
        consumption_source: str = "historical" if consumption_forecast else "unavailable"

        battery_avail: float | None = None
        if battery_capacity_kwh is not None and battery_soc_pct is not None:
            battery_avail = battery_capacity_kwh * max(0.0, (100.0 - battery_soc_pct) / 100.0)

        surplus: float | None = None
        deficit: float | None = None
        if house is not None:
            net = solar - house
            if ev_required_kwh:
                net -= ev_required_kwh
            if net >= 0:
                surplus = net
            else:
                deficit = abs(net)

        return SolarEnergyBudget(
            site_id=forecast.site_id,
            forecast_solar_kwh=solar,
            expected_house_consumption_kwh=house,
            ev_required_kwh=ev_required_kwh,
            battery_available_capacity_kwh=battery_avail,
            expected_surplus_kwh=surplus,
            expected_deficit_kwh=deficit,
            confidence=forecast.confidence,
            quality=forecast.quality,
            consumption_source=consumption_source,  # type: ignore[arg-type]
        )
