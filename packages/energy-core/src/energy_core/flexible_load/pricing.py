"""Per-block marginal cost calculation for flexible loads."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.config import Settings, get_settings
from energy_core.flexible_load.types import EnergySource, HorizonBlock


def eur_to_sek(value_eur: float, settings: Settings | None = None) -> float:
    cfg = settings or get_settings()
    return value_eur * cfg.eur_to_sek_rate


@dataclass(frozen=True, slots=True)
class BlockLoadCost:
    primary_source: EnergySource
    marginal_cost_sek_kwh: float
    solar_share: float
    battery_share: float
    grid_share: float


def price_eur_kwh(block: HorizonBlock) -> float | None:
    return block.all_in_price_eur_kwh or block.spot_price_eur_kwh


def compute_block_load_cost(
    block: HorizonBlock,
    *,
    load_power_w: float,
    allow_battery: bool,
    min_battery_soc_pct: float,
    fallback_price_sek_kwh: float,
    battery_cost_basis_sek_kwh: float = 1.5,
) -> BlockLoadCost:
    """Estimate marginal cost and energy source mix for running load in this block."""
    load_kw = load_power_w / 1000.0
    surplus_kw = max(0.0, block.available_surplus_w / 1000.0)

    solar_kw = min(load_kw, surplus_kw)
    remaining_kw = load_kw - solar_kw

    battery_kw = 0.0
    if remaining_kw > 0 and allow_battery and block.battery_soc_pct is not None:
        if block.battery_soc_pct >= min_battery_soc_pct:
            battery_kw = min(remaining_kw, 2.0)
            remaining_kw -= battery_kw

    grid_kw = max(0.0, remaining_kw)

    total_kw = max(load_kw, 0.001)
    solar_share = solar_kw / total_kw
    battery_share = battery_kw / total_kw
    grid_share = grid_kw / total_kw

    price_eur = price_eur_kwh(block)
    if price_eur is not None:
        grid_cost = eur_to_sek(price_eur)
    else:
        grid_cost = fallback_price_sek_kwh

    export_cost = block.export_value_sek_kwh
    effective_solar_cost = max(0.0, export_cost * 0.5)

    marginal = (
        solar_share * effective_solar_cost
        + battery_share * battery_cost_basis_sek_kwh
        + grid_share * grid_cost
    )

    if solar_share >= 0.8:
        source = EnergySource.SOLAR
    elif battery_share >= 0.5:
        source = EnergySource.BATTERY
    elif grid_share >= 0.8:
        source = EnergySource.GRID
    else:
        source = EnergySource.MIXED

    return BlockLoadCost(
        primary_source=source,
        marginal_cost_sek_kwh=marginal,
        solar_share=solar_share,
        battery_share=battery_share,
        grid_share=grid_share,
    )
