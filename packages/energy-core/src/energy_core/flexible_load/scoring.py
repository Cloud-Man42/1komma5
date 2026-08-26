"""Block scoring for flexible load optimization."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.charging.smart_schedule import GREEN_PRICE_RATIO, RED_PRICE_RATIO
from energy_core.flexible_load.deadline import DeadlineUrgency
from energy_core.flexible_load.pricing import BlockLoadCost
from energy_core.flexible_load.types import EnergySource, FlexibleLoad, HorizonBlock, ScoredBlock


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    solar_surplus: float = 3.0
    low_price: float = 2.0
    battery_availability: float = 1.0
    deadline: float = 2.5
    grid_import: float = 2.0
    battery_depletion: float = 1.5
    export_opportunity: float = 1.0


DEFAULT_WEIGHTS = ScoringWeights()


def score_block(
    block: HorizonBlock,
    load: FlexibleLoad,
    *,
    urgency: DeadlineUrgency,
    load_cost: BlockLoadCost,
    allow_battery: bool,
    min_battery_soc_pct: float,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> ScoredBlock:
    """Score a single horizon block for running the flexible load."""
    surplus_kw = block.available_surplus_w / 1000.0
    load_kw = load.nominal_power_w / 1000.0

    solar_surplus_score = 0.0
    if surplus_kw >= load_kw:
        solar_surplus_score = weights.solar_surplus * min(surplus_kw / max(load_kw, 0.001), 3.0)
    elif surplus_kw > 0:
        solar_surplus_score = weights.solar_surplus * (surplus_kw / max(load_kw, 0.001)) * 0.5

    low_price_score = 0.0
    price = block.all_in_price_eur_kwh or block.spot_price_eur_kwh
    if price is not None and not block.price_estimated:
        if price <= 0.15:
            low_price_score = weights.low_price * 2.0
        elif price <= 0.25:
            low_price_score = weights.low_price
        elif price >= 0.35 * RED_PRICE_RATIO:
            low_price_score = -weights.low_price

    battery_availability_score = 0.0
    battery_depletion_penalty = 0.0
    if block.battery_soc_pct is not None:
        if block.battery_soc_pct >= min_battery_soc_pct + 20:
            battery_availability_score = weights.battery_availability
        elif block.battery_soc_pct >= min_battery_soc_pct and allow_battery:
            battery_availability_score = weights.battery_availability * 0.5
        elif block.battery_soc_pct < min_battery_soc_pct:
            battery_depletion_penalty = weights.battery_depletion * 2.0
        elif block.battery_soc_pct < min_battery_soc_pct + 10:
            battery_depletion_penalty = weights.battery_depletion

    deadline_score = weights.deadline * max(0.0, 1.0 - urgency.hours_remaining / 24.0)

    grid_import_penalty = 0.0
    if surplus_kw < load_kw:
        deficit_kw = load_kw - max(0.0, surplus_kw)
        grid_import_penalty = weights.grid_import * deficit_kw

    export_opportunity_penalty = 0.0
    if surplus_kw > load_kw and block.export_value_sek_kwh > 0:
        export_opportunity_penalty = weights.export_opportunity * (surplus_kw - load_kw)

    total = (
        solar_surplus_score
        + low_price_score
        + battery_availability_score
        + deadline_score
        - grid_import_penalty
        - battery_depletion_penalty
        - export_opportunity_penalty
    )

    if block.price_estimated:
        total *= 0.7

    load_feasible = True
    if urgency.cost_ceiling_sek_kwh is not None and load_cost.marginal_cost_sek_kwh > urgency.cost_ceiling_sek_kwh:
        if not urgency.run_regardless:
            load_feasible = solar_surplus_score > 0

    return ScoredBlock(
        block=block,
        score=total,
        solar_surplus_score=solar_surplus_score,
        low_price_score=low_price_score,
        battery_availability_score=battery_availability_score,
        deadline_score=deadline_score,
        grid_import_penalty=grid_import_penalty,
        battery_depletion_penalty=battery_depletion_penalty,
        export_opportunity_penalty=export_opportunity_penalty,
        expected_energy_source=load_cost.primary_source,
        marginal_cost_sek_kwh=load_cost.marginal_cost_sek_kwh,
        load_feasible=load_feasible,
    )


def is_green_price(price: float, average: float | None) -> bool:
    if average is None or average <= 0:
        return False
    return price <= average * GREEN_PRICE_RATIO
