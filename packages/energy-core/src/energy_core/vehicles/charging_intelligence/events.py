"""In-process charging intelligence events."""

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


class ChargingEventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.name, []):
            handler(event)
