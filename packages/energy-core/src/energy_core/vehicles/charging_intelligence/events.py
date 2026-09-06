"""In-process charging intelligence events (shim — canonical home: platform.events.bus)."""

from energy_core.platform.events.bus import ChargingEventBus, DomainEvent, EventHandler

__all__ = ["ChargingEventBus", "DomainEvent", "EventHandler"]
