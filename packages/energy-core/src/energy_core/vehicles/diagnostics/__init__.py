"""Vehicle integration diagnostics and self-healing."""

from energy_core.vehicles.diagnostics.events import (
    IntegrationEventDraft,
    IntegrationEventSeverity,
    IntegrationEventType,
    PersistStateDiagnostics,
    SelfHealAction,
    SelfHealResult,
)
from energy_core.vehicles.diagnostics.self_heal import evaluate_vehicle_self_heal

__all__ = [
    "IntegrationEventDraft",
    "IntegrationEventSeverity",
    "IntegrationEventType",
    "PersistStateDiagnostics",
    "SelfHealAction",
    "SelfHealResult",
    "evaluate_vehicle_self_heal",
]
