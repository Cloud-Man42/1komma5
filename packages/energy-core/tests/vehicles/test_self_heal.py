"""Tests for vehicle self-heal diagnostics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.diagnostics.events import IntegrationEventType, SelfHealAction
from energy_core.vehicles.diagnostics.self_heal import evaluate_vehicle_self_heal


def test_stale_soc_triggers_force_rest_sync():
    now = datetime.now(UTC)
    latest = VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=31.0,
        soc_updated_at=now - timedelta(minutes=20),
        last_vehicle_update=now - timedelta(minutes=1),
        connection_state="CONNECTED",
        data_quality="MEASURED",
    )
    result = evaluate_vehicle_self_heal(latest=latest, now=now)
    assert SelfHealAction.FORCE_REST_SYNC in result.actions
    assert any(event.event_type == IntegrationEventType.SOC_STALE for event in result.events)


def test_stale_soc_and_range_triggers_ws_reconnect():
    now = datetime.now(UTC)
    latest = VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=31.0,
        electric_range_km=131.0,
        soc_updated_at=now - timedelta(minutes=20),
        range_updated_at=now - timedelta(minutes=20),
        last_vehicle_update=now - timedelta(minutes=1),
        connection_state="CONNECTED",
        data_quality="MEASURED",
    )
    result = evaluate_vehicle_self_heal(latest=latest, now=now)
    assert SelfHealAction.FORCE_WS_RECONNECT in result.actions
    assert any(event.event_type == IntegrationEventType.WS_RECONNECT_REQUESTED for event in result.events)


def test_fresh_soc_does_not_force_rest_sync():
    now = datetime.now(UTC)
    latest = VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=37.0,
        soc_updated_at=now - timedelta(minutes=1),
        last_vehicle_update=now - timedelta(minutes=1),
        connection_state="CONNECTED",
        data_quality="MEASURED",
    )
    result = evaluate_vehicle_self_heal(latest=latest, now=now)
    assert SelfHealAction.FORCE_REST_SYNC not in result.actions
