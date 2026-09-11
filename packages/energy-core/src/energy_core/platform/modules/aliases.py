"""Legacy module_id aliases for backward compatibility."""

from __future__ import annotations

LEGACY_MODULE_ALIASES: dict[str, str] = {
    "charging": "feature.smart-charging",
    "vehicles": "feature.vehicles",
    "spa_energy": "feature.spa-energy",
    "energy_balance": "feature.energy-balance",
    "solar_forecast": "feature.solar-forecast",
    "price_engine": "feature.price-engine",
}

CANONICAL_TO_LEGACY: dict[str, str] = {v: k for k, v in LEGACY_MODULE_ALIASES.items()}


def canonical_module_id(module_id: str) -> str:
    return LEGACY_MODULE_ALIASES.get(module_id, module_id)


def resolve_module_id(module_id: str) -> str:
    """Accept legacy or canonical ids."""
    return canonical_module_id(module_id)
