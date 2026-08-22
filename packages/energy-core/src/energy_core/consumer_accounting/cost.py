"""Consumer cost calculation — wraps EV cost engine."""

from __future__ import annotations

from energy_core.ev_accounting.cost import EVChargingCostCalculator
from energy_core.ev_accounting.models import EnergyAttribution, IntervalCostResult

ConsumerCostCalculator = EVChargingCostCalculator

__all__ = ["ConsumerCostCalculator", "EnergyAttribution", "IntervalCostResult"]
