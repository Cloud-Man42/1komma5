"""Energy balance domain types."""

from __future__ import annotations

from enum import StrEnum


class EnergyBalanceStatus(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    ALIGNMENT_FAILED = "ALIGNMENT_FAILED"
    RESIDUAL_HIGH = "RESIDUAL_HIGH"
    POSSIBLE_DOUBLE_COUNTING = "POSSIBLE_DOUBLE_COUNTING"
