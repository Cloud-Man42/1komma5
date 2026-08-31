"""Energy source priority for charging sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EnergySource(StrEnum):
    CHARGER_METER = "CHARGER_METER"
    MERCEDES = "MERCEDES"
    POWER_INTEGRATION = "POWER_INTEGRATION"
    SOC_ESTIMATE = "SOC_ESTIMATE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SessionEnergyEstimate:
    energy_kwh: float | None
    estimated_energy_kwh: float | None
    energy_source: EnergySource
    quality: str


def resolve_session_energy(
    *,
    charger_meter_kwh: float | None,
    mercedes_energy_kwh: float | None,
    integrated_power_kwh: float | None,
    soc_estimate_kwh: float | None,
) -> SessionEnergyEstimate:
    if charger_meter_kwh is not None and charger_meter_kwh > 0:
        return SessionEnergyEstimate(charger_meter_kwh, None, EnergySource.CHARGER_METER, "MEASURED")
    if mercedes_energy_kwh is not None and mercedes_energy_kwh > 0:
        return SessionEnergyEstimate(mercedes_energy_kwh, None, EnergySource.MERCEDES, "MEASURED")
    if integrated_power_kwh is not None and integrated_power_kwh > 0:
        return SessionEnergyEstimate(integrated_power_kwh, integrated_power_kwh, EnergySource.POWER_INTEGRATION, "ESTIMATED")
    if soc_estimate_kwh is not None and soc_estimate_kwh > 0:
        return SessionEnergyEstimate(soc_estimate_kwh, soc_estimate_kwh, EnergySource.SOC_ESTIMATE, "ESTIMATED")
    return SessionEnergyEstimate(None, None, EnergySource.UNKNOWN, "UNKNOWN")
