"""Platform event bus tests."""

from datetime import UTC, datetime

from energy_core.platform.events.bus import ChargingEventBus, DomainEvent, get_event_bus, reset_event_bus
from energy_core.vehicles.charging_intelligence.events import ChargingEventBus as ShimBus


def test_publish_delivers_to_subscriber() -> None:
    bus = ChargingEventBus()
    received: list[str] = []

    bus.subscribe("test.event", lambda event: received.append(event.name))
    bus.publish(
        DomainEvent(
            name="test.event",
            payload={"value": 1},
            occurred_at=datetime.now(UTC),
        )
    )
    assert received == ["test.event"]


def test_shim_reexports_platform_bus() -> None:
    assert ShimBus is ChargingEventBus


def test_get_event_bus_returns_singleton() -> None:
    reset_event_bus()
    assert get_event_bus() is get_event_bus()
    reset_event_bus()
