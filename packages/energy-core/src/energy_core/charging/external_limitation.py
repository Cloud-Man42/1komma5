"""Detect stable external limitation without guessing Charge Amps reason fields."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

EXTERNAL_LIMIT_TOLERANCE_A = 1.0
EXTERNAL_LIMIT_STABLE_SECONDS = 45.0


@dataclass
class ExternalLimitationTracker:
    limited_since: datetime | None = None

    def update(
        self,
        *,
        requested_current_a: float,
        configured_current_a: float | None,
        actual_charging_current_a: float | None,
        is_charging: bool,
        now: datetime,
    ) -> bool:
        if not is_charging or requested_current_a <= 0:
            self.limited_since = None
            return False
        if actual_charging_current_a is None:
            self.limited_since = None
            return False

        reference = (
            configured_current_a if configured_current_a is not None else requested_current_a
        )
        if reference - actual_charging_current_a < EXTERNAL_LIMIT_TOLERANCE_A:
            self.limited_since = None
            return False

        if self.limited_since is None:
            self.limited_since = now
        elapsed = (now - self.limited_since).total_seconds()
        return elapsed >= EXTERNAL_LIMIT_STABLE_SECONDS


def max_phase_current(
    l1: float | None,
    l2: float | None,
    l3: float | None,
) -> float | None:
    values = [value for value in (l1, l2, l3) if value is not None and value > 0]
    if not values:
        return None
    return max(values)
