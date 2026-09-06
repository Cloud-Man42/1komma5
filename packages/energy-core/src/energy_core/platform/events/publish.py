"""Helpers for publishing domain events through the platform bus."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from energy_core.platform.events.bus import DomainEvent, get_event_bus
from energy_core.platform.events.types import (
    CHARGER_STATUS_CHANGED,
    CHARGING_SESSION_STARTED,
    CHARGING_SESSION_STOPPED,
    INTEGRATION_HEALTH_CHANGED,
    VEHICLE_STATE_CHANGED,
)


def publish_domain_event(name: str, payload: dict[str, Any]) -> None:
    get_event_bus().publish(
        DomainEvent(
            name=name,
            payload=payload,
            occurred_at=datetime.now(UTC),
        )
    )


def publish_charging_session_started(
    *,
    session_kind: str,
    site_id: int,
    session_id: int,
    **extra: Any,
) -> None:
    publish_domain_event(
        CHARGING_SESSION_STARTED,
        {
            "session_kind": session_kind,
            "site_id": site_id,
            "session_id": session_id,
            **extra,
        },
    )


def publish_charging_session_stopped(
    *,
    session_kind: str,
    site_id: int,
    session_id: int,
    **extra: Any,
) -> None:
    publish_domain_event(
        CHARGING_SESSION_STOPPED,
        {
            "session_kind": session_kind,
            "site_id": site_id,
            "session_id": session_id,
            **extra,
        },
    )


def publish_vehicle_state_changed(
    *,
    vehicle_id: int,
    site_id: int,
    is_plugged_in: bool | None,
    is_charging: bool | None,
    previous_plugged_in: bool | None,
    previous_charging: bool | None,
) -> None:
    publish_domain_event(
        VEHICLE_STATE_CHANGED,
        {
            "vehicle_id": vehicle_id,
            "site_id": site_id,
            "is_plugged_in": is_plugged_in,
            "is_charging": is_charging,
            "previous_plugged_in": previous_plugged_in,
            "previous_charging": previous_charging,
        },
    )


def publish_integration_health_changed(
    *,
    site_id: int,
    provider: str,
    status: str,
    previous_status: str | None,
) -> None:
    publish_domain_event(
        INTEGRATION_HEALTH_CHANGED,
        {
            "site_id": site_id,
            "provider": provider,
            "status": status,
            "previous_status": previous_status,
        },
    )


def publish_charger_status_changed(
    *,
    site_id: int,
    charger_id: int,
    previous_state: str | None,
    new_state: str | None,
) -> None:
    publish_domain_event(
        CHARGER_STATUS_CHANGED,
        {
            "site_id": site_id,
            "charger_id": charger_id,
            "previous_state": previous_state,
            "new_state": new_state,
        },
    )
