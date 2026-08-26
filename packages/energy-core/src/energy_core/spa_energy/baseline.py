"""Baseline cost without smart control."""

from __future__ import annotations

from energy_core.flexible_load.types import HorizonBlock, ScoredBlock
from energy_core.spa_energy.estimate import estimate_cleaning_window
from energy_core.integrations.arctic_spa.config import SpaPowerProfiles


def baseline_cleaning_cost_sek(
    *,
    runtime_hours: float,
    power_profiles: SpaPowerProfiles,
    scored_blocks: tuple[ScoredBlock, ...],
    fallback_price_sek_kwh: float,
) -> float:
    """Cost if cleaning ran at average conditions (no optimization)."""
    if scored_blocks:
        avg_cost = sum(b.marginal_cost_sek_kwh for b in scored_blocks) / len(scored_blocks)
    else:
        avg_cost = fallback_price_sek_kwh

    from datetime import timedelta

    estimate = estimate_cleaning_window(
        duration=timedelta(hours=runtime_hours),
        power_profiles=power_profiles,
        marginal_cost_sek_kwh=avg_cost,
    )
    return estimate.cost_sek


def average_block_price_sek(blocks: tuple[HorizonBlock, ...], fallback: float) -> float:
    from energy_core.flexible_load.pricing import eur_to_sek, price_eur_kwh

    prices = [eur_to_sek(p) for b in blocks if (p := price_eur_kwh(b)) is not None]
    if not prices:
        return fallback
    return sum(prices) / len(prices)
