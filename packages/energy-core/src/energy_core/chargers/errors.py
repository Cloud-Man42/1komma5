"""Normalized Charge Amps / charger API errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChargerApiErrorCode = Literal[
    "AUTH_ERROR",
    "RATE_LIMITED",
    "CHARGER_OFFLINE",
    "TIMEOUT",
    "INVALID_RESPONSE",
    "COMMAND_REJECTED",
    "UNKNOWN",
]


@dataclass(frozen=True, slots=True)
class ChargerApiError(Exception):
    code: ChargerApiErrorCode
    message: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message
