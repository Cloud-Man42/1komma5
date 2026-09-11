"""Broker types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrokerDecision:
    allowed: bool
    message: str = ""
    data: dict | None = None
