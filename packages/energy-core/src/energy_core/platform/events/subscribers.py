"""Default in-process domain event subscribers."""

from __future__ import annotations

import logging

from energy_core.platform.events.bus import ChargingEventBus, DomainEvent
from energy_core.platform.events.site_refresh import mark_site_dirty
from energy_core.platform.events.types import (
    CHARGER_STATUS_CHANGED,
    CHARGING_SESSION_STARTED,
    CHARGING_SESSION_STOPPED,
    INTEGRATION_HEALTH_CHANGED,
    VEHICLE_STATE_CHANGED,
)

logger = logging.getLogger(__name__)

_DEFAULT_EVENT_NAMES = (
    CHARGING_SESSION_STARTED,
    CHARGING_SESSION_STOPPED,
    VEHICLE_STATE_CHANGED,
    CHARGER_STATUS_CHANGED,
    INTEGRATION_HEALTH_CHANGED,
)

_REFRESH_EVENT_NAMES = frozenset(
    {
        CHARGING_SESSION_STARTED,
        CHARGING_SESSION_STOPPED,
        VEHICLE_STATE_CHANGED,
        CHARGER_STATUS_CHANGED,
        INTEGRATION_HEALTH_CHANGED,
    }
)


def _log_domain_event(event: DomainEvent) -> None:
    logger.info("domain_event name=%s payload=%s", event.name, event.payload)


def _mark_site_refresh(event: DomainEvent) -> None:
    site_id = event.payload.get("site_id")
    if isinstance(site_id, int):
        mark_site_dirty(site_id)


def register_default_subscribers(bus: ChargingEventBus) -> None:
    for event_name in _DEFAULT_EVENT_NAMES:
        bus.subscribe(event_name, _log_domain_event)
    for event_name in _REFRESH_EVENT_NAMES:
        bus.subscribe(event_name, _mark_site_refresh)
