"""Energy control interface — safe dry-run foundation for future automation."""

from energy_core.energy_control.gate import (
    mode_allows_automatic_apply,
    mode_allows_manual_apply,
    mode_allows_preview,
)
from energy_core.energy_control.mapper import action_from_strategy
from energy_core.energy_control.noop_provider import NoopControlProvider, default_control_provider
from energy_core.energy_control.provider import IEnergyControlProvider
from energy_core.energy_control.service import EnergyControlService
from energy_core.energy_control.types import (
    ControlActionRecord,
    ControlOutcome,
    ControlResult,
    ControlStatus,
    ControlTarget,
    OptimizationAction,
)

__all__ = [
    "ControlActionRecord",
    "ControlOutcome",
    "ControlResult",
    "ControlStatus",
    "ControlTarget",
    "EnergyControlService",
    "IEnergyControlProvider",
    "NoopControlProvider",
    "OptimizationAction",
    "action_from_strategy",
    "default_control_provider",
    "mode_allows_automatic_apply",
    "mode_allows_manual_apply",
    "mode_allows_preview",
]
