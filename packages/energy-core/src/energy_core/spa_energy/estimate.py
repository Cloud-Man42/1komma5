"""Energy and cost estimation for planned spa windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from energy_core.consumer_accounting.types import DataQuality
from energy_core.integrations.arctic_spa.config import SpaPowerProfiles


@dataclass(frozen=True, slots=True)
class SpaWindowEstimate:
    energy_kwh: float
    cost_sek: float
    solar_share: float
    battery_share: float
    grid_share: float
    quality: DataQuality = DataQuality.ESTIMATED


def estimate_cleaning_window(
    *,
    duration: timedelta,
    power_profiles: SpaPowerProfiles,
    marginal_cost_sek_kwh: float,
    solar_share: float = 0.0,
    battery_share: float = 0.0,
    grid_share: float = 1.0,
) -> SpaWindowEstimate:
    """Estimate kWh for a cleaning window using nominal circulation + heater power."""
    hours = duration.total_seconds() / 3600.0
    nominal_w = power_profiles.circulation_w + power_profiles.heater_w * 0.3
    energy_kwh = (nominal_w / 1000.0) * hours
    cost = energy_kwh * marginal_cost_sek_kwh
    return SpaWindowEstimate(
        energy_kwh=energy_kwh,
        cost_sek=cost,
        solar_share=solar_share,
        battery_share=battery_share,
        grid_share=grid_share,
        quality=DataQuality.ESTIMATED,
    )
