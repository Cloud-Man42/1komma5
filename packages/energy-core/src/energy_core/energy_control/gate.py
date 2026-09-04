"""Optimization mode gating for control actions."""

from __future__ import annotations

from energy_core.energy_control.types import ControlOutcome
from energy_core.price_engine.types import OptimizationMode


def mode_allows_preview(mode: OptimizationMode) -> bool:
    return mode in {
        OptimizationMode.RECOMMEND,
        OptimizationMode.SEMI_AUTOMATIC,
        OptimizationMode.AUTOMATIC,
    }


def mode_allows_manual_apply(mode: OptimizationMode, *, control_enabled: bool) -> bool:
    if not control_enabled:
        return False
    return mode in {OptimizationMode.SEMI_AUTOMATIC, OptimizationMode.AUTOMATIC}


def mode_allows_automatic_apply(mode: OptimizationMode, *, control_enabled: bool) -> bool:
    if not control_enabled:
        return False
    return mode == OptimizationMode.AUTOMATIC


def reject_outcome_for_mode(mode: OptimizationMode, *, control_enabled: bool, automatic: bool) -> ControlOutcome:
    if mode == OptimizationMode.MONITOR_ONLY:
        return ControlOutcome.SKIPPED
    if not control_enabled:
        return ControlOutcome.REJECTED
    if automatic and mode != OptimizationMode.AUTOMATIC:
        return ControlOutcome.REJECTED
    if not automatic and mode == OptimizationMode.RECOMMEND:
        return ControlOutcome.REJECTED
    return ControlOutcome.REJECTED
