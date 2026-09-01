"""Structured vehicle integration diagnostic events."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class IntegrationEventSeverity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ACTION = "ACTION"
    ERROR = "ERROR"


class IntegrationEventType(StrEnum):
    SOC_UPDATED = "SOC_UPDATED"
    SOC_UNCHANGED = "SOC_UNCHANGED"
    SOC_NOT_IN_MESSAGE = "SOC_NOT_IN_MESSAGE"
    SOC_LKG_KEPT = "SOC_LKG_KEPT"
    SOC_STALE = "SOC_STALE"
    SOC_HIDDEN_STALE = "SOC_HIDDEN_STALE"
    TELEMETRY_SKIPPED = "TELEMETRY_SKIPPED"
    SANITIZED_PLACEHOLDER = "SANITIZED_PLACEHOLDER"
    CONNECTION_HEALED = "CONNECTION_HEALED"
    POLLING_MODE = "POLLING_MODE"
    REST_SYNC = "REST_SYNC"
    REST_SYNC_FAILED = "REST_SYNC_FAILED"
    REST_SYNC_FORCED = "REST_SYNC_FORCED"
    SESSION_REPAIR = "SESSION_REPAIR"


class SelfHealAction(StrEnum):
    FORCE_REST_SYNC = "FORCE_REST_SYNC"


@dataclass(frozen=True, slots=True)
class IntegrationEventDraft:
    event_type: IntegrationEventType
    severity: IntegrationEventSeverity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def details_json(self) -> str:
        return json.dumps(self.details, default=str)


@dataclass(frozen=True, slots=True)
class PersistStateDiagnostics:
    events: tuple[IntegrationEventDraft, ...] = ()


@dataclass(frozen=True, slots=True)
class SelfHealResult:
    events: tuple[IntegrationEventDraft, ...] = ()
    actions: tuple[SelfHealAction, ...] = ()
