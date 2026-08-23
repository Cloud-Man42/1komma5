"""EV charging cost and savings calculations."""

from __future__ import annotations

from energy_core.ev_accounting.constants import DEFAULT_SAVINGS_BASELINE
from energy_core.ev_accounting.models import EnergyAttribution, IntervalCostResult


class EVChargingCostCalculator:
    """
    Compute actual cash cost, opportunity cost, and reference baseline cost.

    ACTUAL_CASH_COST: grid_direct × price + grid_battery × ledger avg cost
    OPPORTUNITY_COST: solar_direct × export compensation
    Reference (IMMEDIATE_GRID_CHARGING): all energy × interval price
    """

    def interval_costs(
        self,
        attribution: EnergyAttribution,
        *,
        grid_price_sek_kwh: float | None,
        grid_battery_avg_cost_sek_kwh: float | None,
        export_compensation_sek_kwh: float,
        baseline: str = DEFAULT_SAVINGS_BASELINE,
    ) -> IntervalCostResult:
        price = grid_price_sek_kwh
        grid_direct_cost = 0.0
        grid_battery_cost = 0.0
        if price is not None:
            grid_direct_cost = attribution.grid_direct_kwh * price
        if grid_battery_avg_cost_sek_kwh is not None:
            grid_battery_cost = attribution.grid_battery_kwh * grid_battery_avg_cost_sek_kwh

        actual_cash = grid_direct_cost + grid_battery_cost
        opportunity = attribution.solar_direct_kwh * export_compensation_sek_kwh

        reference: float | None = None
        savings: float | None = None
        if (
            baseline == DEFAULT_SAVINGS_BASELINE
            and price is not None
            or baseline == "AVERAGE_GRID_PRICE"
            and price is not None
        ):
            reference = attribution.total_kwh * price
            savings = reference - actual_cash

        return IntervalCostResult(
            actual_cash_cost_sek=round(actual_cash, 4),
            opportunity_cost_sek=round(opportunity, 4),
            reference_cost_sek=round(reference, 4) if reference is not None else None,
            savings_sek=round(savings, 4) if savings is not None else None,
        )

    def solar_contribution_sek(
        self,
        attribution: EnergyAttribution,
        *,
        grid_price_sek_kwh: float | None,
    ) -> float:
        """Avoided grid purchase value from solar used for EV (separate from smart charging savings)."""
        if grid_price_sek_kwh is None:
            return 0.0
        solar_kwh = attribution.solar_direct_kwh + attribution.solar_battery_kwh
        return round(solar_kwh * grid_price_sek_kwh, 4)

    @staticmethod
    def aggregate_session_costs(
        intervals: list[IntervalCostResult],
    ) -> tuple[float, float, float | None, float | None]:
        actual = sum(i.actual_cash_cost_sek for i in intervals)
        opportunity = sum(i.opportunity_cost_sek for i in intervals)
        refs = [i.reference_cost_sek for i in intervals if i.reference_cost_sek is not None]
        reference = sum(refs) if refs else None
        savings = (reference - actual) if reference is not None else None
        return (
            round(actual, 2),
            round(opportunity, 2),
            round(reference, 2) if reference else None,
            round(savings, 2) if savings is not None else None,
        )
