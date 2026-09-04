"""Energy control domain types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.types import OptimizationMode, StrategyState

OptimizationAction = EnergyAction


class ControlTarget(StrEnum):
    SITE = "site"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"


class ControlOutcome(StrEnum):
    PREVIEW = "PREVIEW"
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ControlResult:
    action: OptimizationAction
    target: ControlTarget
    outcome: ControlOutcome
    dry_run: bool
    reason: str
    reason_sv: str
    provider: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlActionRecord:
    id: int
    site_id: int
    recorded_at: datetime
    optimization_mode: OptimizationMode
    action: OptimizationAction
    target: ControlTarget
    outcome: ControlOutcome
    dry_run: bool
    reason: str | None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ControlStatus:
    site_id: int
    optimization_mode: OptimizationMode
    control_enabled: bool
    writes_allowed: bool
    automatic_allowed: bool
    provider: str
    last_action: ControlActionRecord | None = None
