"""Spa actuator runtime types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SpaActuatorState(StrEnum):
    IDLE = "IDLE"
    WAITING = "WAITING"
    CLEANING = "CLEANING"
    COOLDOWN = "COOLDOWN"
    DEGRADED = "DEGRADED"
    MANUAL = "MANUAL"


@dataclass
class SpaActuatorRuntime:
    state: SpaActuatorState = SpaActuatorState.IDLE
    cleaning_started_at: datetime | None = None
    cleaning_stop_at: datetime | None = None
    last_command_at: datetime | None = None
    last_stop_at: datetime | None = None
    starts_today: int = 0
    starts_day: str = ""
    manual_override_until: datetime | None = None
    filter_held_off_until: datetime | None = None
    last_planner_run_at: datetime | None = None
    integration_degraded: bool = False
    integration_degraded_message_sv: str = ""
    last_reason: str = ""
    last_reason_sv: str = ""


DEGRADED_MESSAGE_SV = (
    "Arctic Spa smartstyrning är tillfälligt otillgänglig. "
    "Spaet använder sitt ordinarie interna cleaning-schema."
)
