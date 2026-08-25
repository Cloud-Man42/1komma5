"""Tests for EMIC vehicle correlation in Heartbeat discovery."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.heartbeat.bridge.emic_context import enrich_discovery_with_emic_vehicles
from energy_core.heartbeat.discovery.models import (
    BridgeLifecycleState,
    HeartbeatEvDiscoveryResult,
    ResolvedEvId,
    SetupClassification,
)


def _base_result() -> HeartbeatEvDiscoveryResult:
    return HeartbeatEvDiscoveryResult(
        site_slug="akarp",
        site_name="Åkarp",
        system_id="sys",
        authenticated=True,
        ev_profiles=(),
        wallboxes=(),
        ems_devices=(),
        assignments=(),
        charging_modes=("SMART_CHARGE",),
        ai_decision_types=(),
        ai_decisions_found=False,
        resolved_ev_id=ResolvedEvId(None, 0.0, "none", None, ()),
        setup_classification=SetupClassification.EV_ID_NOT_FOUND,
        bridge_lifecycle=BridgeLifecycleState.DISCOVERY,
        halo_found=True,
        halo_online=True,
        virtual_bridge_suitable=False,
        warnings=("No EV profiles found in Heartbeat",),
        observations=(),
        field_hints=(),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_enrich_adds_emic_vehicle_and_warning():
    session = MagicMock()
    vehicle = MagicMock()
    vehicle.id = 2
    vehicle.provider = "mercedes"
    vehicle.display_name = "Mercedes-Benz"
    vehicle.manufacturer = "Mercedes-Benz"
    vehicle.model = "EQE 500"

    state = MagicMock()
    state.connection_state = "CONNECTED"
    state.state_of_charge_percent = 72.0

    repo = MagicMock()
    repo.list_for_site = AsyncMock(return_value=[vehicle])
    repo.get_latest_state = AsyncMock(return_value=state)

    import energy_core.heartbeat.bridge.emic_context as emic_context

    original = emic_context.VehicleRepository
    emic_context.VehicleRepository = lambda _session: repo
    try:
        enriched = await enrich_discovery_with_emic_vehicles(session, 1, _base_result())
    finally:
        emic_context.VehicleRepository = original

    assert enriched.emic_vehicle_lines
    assert "mercedes" in enriched.emic_vehicle_lines[0]
    assert any("EMIC has registered vehicle" in warning for warning in enriched.warnings)
    assert "EMIC has registered vehicle" in enriched.report_text
    assert "EMIC vehicle integration" in enriched.report_text
