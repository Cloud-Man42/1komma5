"""Shared platform runtime for EMIC modular architecture."""

from energy_core.platform.events.bus import ChargingEventBus, DomainEvent, EventHandler
from energy_core.platform.lifecycle import LifecyclePhase, ModuleLifecycle

__all__ = [
    "ChargingEventBus",
    "DomainEvent",
    "EventHandler",
    "LifecyclePhase",
    "ModuleLifecycle",
]
