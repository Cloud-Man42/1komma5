"""Map strategy snapshots to optimization actions."""

from __future__ import annotations

from energy_core.energy_control.types import OptimizationAction
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.strategy import EnergyStrategySnapshot
from energy_core.price_engine.types import StrategyState


def action_from_strategy(snapshot: EnergyStrategySnapshot) -> OptimizationAction | None:
    if snapshot.recommended_action:
        try:
            return EnergyAction(snapshot.recommended_action)
        except ValueError:
            pass

    mapping: dict[StrategyState, OptimizationAction] = {
        StrategyState.CHARGE_BATTERY: EnergyAction.STORE_IN_BATTERY,
        StrategyState.DISCHARGE_BATTERY: EnergyAction.DISCHARGE_BATTERY,
        StrategyState.EXPORT: EnergyAction.EXPORT_TO_GRID,
        StrategyState.CHARGE_VEHICLE: EnergyAction.USE_NOW,
        StrategyState.WAIT: EnergyAction.WAIT,
        StrategyState.PEAK_PROTECTION: EnergyAction.WAIT,
        StrategyState.PEAK_AHEAD: EnergyAction.STORE_IN_BATTERY,
        StrategyState.SAVE_BATTERY: EnergyAction.STORE_IN_BATTERY,
        StrategyState.NORMAL_SELF_USE: EnergyAction.USE_NOW,
    }
    return mapping.get(snapshot.strategy_state)
