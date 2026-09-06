"""In-process domain event bus."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    occurred_at: datetime


EventHandler = Callable[[DomainEvent], None]

_default_bus: ChargingEventBus | None = None


class ChargingEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.name, []):
            handler(event)

    def clear(self) -> None:
        self._handlers.clear()


def get_event_bus() -> ChargingEventBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = ChargingEventBus()
    return _default_bus


def set_event_bus(bus: ChargingEventBus | None) -> None:
    global _default_bus
    _default_bus = bus


def reset_event_bus() -> None:
    global _default_bus
    if _default_bus is not None:
        _default_bus.clear()
    _default_bus = None
