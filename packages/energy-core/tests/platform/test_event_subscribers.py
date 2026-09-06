"""Tests for default domain event subscribers."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.platform.events.bus import ChargingEventBus, DomainEvent
from energy_core.platform.events.site_refresh import drain_dirty_site_ids, reset_dirty_sites
from energy_core.platform.events.subscribers import register_default_subscribers
from energy_core.platform.events.types import CHARGER_STATUS_CHANGED, VEHICLE_STATE_CHANGED


def test_subscriber_marks_site_dirty_on_vehicle_state_change():
    reset_dirty_sites()
    bus = ChargingEventBus()
    register_default_subscribers(bus)
    bus.publish(
        DomainEvent(
            name=VEHICLE_STATE_CHANGED,
            payload={"site_id": 42, "vehicle_id": 7},
            occurred_at=datetime.now(UTC),
        )
    )
    assert drain_dirty_site_ids() == {42}


def test_subscriber_ignores_events_without_site_id():
    reset_dirty_sites()
    bus = ChargingEventBus()
    register_default_subscribers(bus)
    bus.publish(
        DomainEvent(
            name=CHARGER_STATUS_CHANGED,
            payload={"charger_id": 3, "new_state": "CHARGING"},
            occurred_at=datetime.now(UTC),
        )
    )
    assert drain_dirty_site_ids() == set()
