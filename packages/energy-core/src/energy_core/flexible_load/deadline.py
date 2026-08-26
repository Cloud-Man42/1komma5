"""Deadline urgency tiers for flexible load planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DeadlineUrgency:
    hours_remaining: float
    tier: str
    cost_ceiling_sek_kwh: float | None
    min_score: float
    run_regardless: bool


def compute_deadline_urgency(now: datetime, deadline: datetime) -> DeadlineUrgency:
    """Map time-to-deadline to scoring constraints."""
    if now.tzinfo is None or deadline.tzinfo is None:
        delta = deadline - now
    else:
        delta = deadline - now
    hours = max(0.0, delta.total_seconds() / 3600.0)

    if hours < 2.0:
        return DeadlineUrgency(
            hours_remaining=hours,
            tier="critical",
            cost_ceiling_sek_kwh=None,
            min_score=-999.0,
            run_regardless=True,
        )
    if hours < 6.0:
        return DeadlineUrgency(
            hours_remaining=hours,
            tier="urgent",
            cost_ceiling_sek_kwh=8.0,
            min_score=-50.0,
            run_regardless=False,
        )
    if hours < 12.0:
        return DeadlineUrgency(
            hours_remaining=hours,
            tier="moderate",
            cost_ceiling_sek_kwh=5.0,
            min_score=0.0,
            run_regardless=False,
        )
    return DeadlineUrgency(
        hours_remaining=hours,
        tier="relaxed",
        cost_ceiling_sek_kwh=3.0,
        min_score=20.0,
        run_regardless=False,
    )
