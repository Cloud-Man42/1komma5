"""Consumer attribution — wraps EV attribution engine."""

from __future__ import annotations

from energy_core.ev_accounting.attribution import EnergyAttributionEngine

ConsumerAttributionEngine = EnergyAttributionEngine

__all__ = ["ConsumerAttributionEngine"]
