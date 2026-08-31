"""Roll a session's intervals up into the totals stored on the session row.

Shared by session completion in the collector and by the backfill that repairs
sessions written before the meter-reset fix, so both produce identical numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from energy_core.ev_accounting.cost import EVChargingCostCalculator
from energy_core.ev_accounting.models import EnergyAttribution
from energy_core.ev_accounting.reconciliation import SessionReconciliationService


class IntervalLike(Protocol):
    charged_energy_kwh: float
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float
    electricity_price_sek_kwh: float | None
    actual_cost_sek: float
    reference_cost_sek: float | None


@dataclass(frozen=True, slots=True)
class SessionTotals:
    """Every derived field a completed session row carries."""

    total_energy_kwh: float
    solar_direct_kwh: float
    solar_battery_kwh: float
    grid_battery_kwh: float
    grid_direct_kwh: float
    actual_cost_sek: float
    reference_cost_sek: float | None
    savings_sek: float | None
    smart_charging_savings_sek: float | None
    solar_contribution_sek: float
    renewable_share_pct: float
    grid_share_pct: float
    energy_quality: str
    cost_quality: str
    attribution_quality: str
    reconciliation_delta_kwh: float
    reconciliation_note: str

    def as_fields(self) -> dict[str, object]:
        """Column keyword arguments for the session repository."""
        return {
            "total_energy_kwh": self.total_energy_kwh,
            "solar_direct_kwh": self.solar_direct_kwh,
            "solar_battery_kwh": self.solar_battery_kwh,
            "grid_battery_kwh": self.grid_battery_kwh,
            "grid_direct_kwh": self.grid_direct_kwh,
            "actual_cost_sek": self.actual_cost_sek,
            "reference_cost_sek": self.reference_cost_sek,
            "savings_sek": self.savings_sek,
            "smart_charging_savings_sek": self.smart_charging_savings_sek,
            "solar_contribution_sek": self.solar_contribution_sek,
            "renewable_share_pct": self.renewable_share_pct,
            "grid_share_pct": self.grid_share_pct,
            "energy_quality": self.energy_quality,
            "cost_quality": self.cost_quality,
            "attribution_quality": self.attribution_quality,
            "reconciliation_delta_kwh": self.reconciliation_delta_kwh,
            "reconciliation_note": self.reconciliation_note,
        }


def session_totals_from_intervals(
    intervals: list[IntervalLike],
    *,
    measured_kwh: float | None,
    meter_quality: str,
) -> SessionTotals:
    """Sum the intervals, then reconcile against the charger's own meter total."""
    reconciliation = SessionReconciliationService()
    cost_calc = EVChargingCostCalculator()

    attributed_kwh = sum(i.charged_energy_kwh for i in intervals)
    if measured_kwh is None:
        measured_kwh = attributed_kwh
        meter_quality = "ESTIMATED"

    attribution = EnergyAttribution(
        solar_direct_kwh=sum(i.solar_direct_kwh for i in intervals),
        solar_battery_kwh=sum(i.solar_battery_kwh for i in intervals),
        grid_battery_kwh=sum(i.grid_battery_kwh for i in intervals),
        grid_direct_kwh=sum(i.grid_direct_kwh for i in intervals),
    )

    recon = reconciliation.reconcile(
        attribution,
        measured_kwh=measured_kwh,
        attributed_kwh=attributed_kwh,
    )

    actual_cost = sum(i.actual_cost_sek for i in intervals)
    reference_cost = sum(i.reference_cost_sek for i in intervals if i.reference_cost_sek is not None)
    reference_cost = reference_cost if reference_cost > 0 else None
    savings = (reference_cost - actual_cost) if reference_cost is not None else None
    solar_contribution = sum(
        cost_calc.solar_contribution_sek(
            EnergyAttribution(i.solar_direct_kwh, i.solar_battery_kwh, i.grid_battery_kwh, i.grid_direct_kwh),
            grid_price_sek_kwh=i.electricity_price_sek_kwh,
        )
        for i in intervals
    )

    total = recon.attribution.total_kwh or measured_kwh or 0.0
    renewable_pct = (recon.attribution.renewable_kwh / total * 100.0) if total > 0 else 0.0
    grid_pct = (recon.attribution.grid_kwh / total * 100.0) if total > 0 else 0.0

    return SessionTotals(
        total_energy_kwh=total,
        solar_direct_kwh=recon.attribution.solar_direct_kwh,
        solar_battery_kwh=recon.attribution.solar_battery_kwh,
        grid_battery_kwh=recon.attribution.grid_battery_kwh,
        grid_direct_kwh=recon.attribution.grid_direct_kwh,
        actual_cost_sek=actual_cost,
        reference_cost_sek=reference_cost,
        savings_sek=savings,
        smart_charging_savings_sek=savings,
        solar_contribution_sek=solar_contribution,
        renewable_share_pct=renewable_pct,
        grid_share_pct=grid_pct,
        energy_quality=recon.energy_quality if meter_quality == "MEASURED" else meter_quality,
        cost_quality="CALCULATED" if reference_cost else "INCOMPLETE",
        attribution_quality="CALCULATED",
        reconciliation_delta_kwh=recon.delta_kwh,
        reconciliation_note=recon.note,
    )
