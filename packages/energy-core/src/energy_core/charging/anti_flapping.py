"""Anti-flapping helpers for charger current commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class AntiFlappingConfig:
    min_change_interval_seconds: float = 60.0
    current_hysteresis_a: float = 1.0


@dataclass
class AntiFlappingState:
    last_applied_current_a: float | None = None
    last_change_at: datetime | None = None
    last_command_current_a: float | None = None


def should_apply_current(
    requested_a: float,
    state: AntiFlappingState,
    config: AntiFlappingConfig,
    *,
    now: datetime | None = None,
) -> tuple[bool, float, str]:
    now = now or datetime.now(UTC)
    requested_a = max(0.0, requested_a)

    if state.last_command_current_a is not None and abs(state.last_command_current_a - requested_a) < 0.01:
        return False, state.last_applied_current_a or 0.0, "duplicate_command"

    if state.last_applied_current_a is not None:
        delta = abs(requested_a - state.last_applied_current_a)
        if delta < config.current_hysteresis_a:
            return False, state.last_applied_current_a, "hysteresis"

    if state.last_change_at is not None:
        elapsed = (now - state.last_change_at).total_seconds()
        if elapsed < config.min_change_interval_seconds:
            return False, state.last_applied_current_a or 0.0, "min_interval"

    return True, requested_a, "apply"


def record_applied(state: AntiFlappingState, current_a: float, *, now: datetime | None = None) -> None:
    now = now or datetime.now(UTC)
    state.last_applied_current_a = current_a
    state.last_command_current_a = current_a
    state.last_change_at = now
