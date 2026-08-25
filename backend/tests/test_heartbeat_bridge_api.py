"""Backend API tests for Heartbeat Virtual EV Bridge."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_discovery_requires_system_id(client):
    ac, _, _ = client
    response = await ac.post("/api/sites/summer-house-denmark/heartbeat/discovery/run")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_discovery_run_success(client):
    from datetime import UTC, datetime

    from energy_core.heartbeat.discovery.models import (
        BridgeLifecycleState,
        HeartbeatEvDiscoveryResult,
        ResolvedEvId,
        SetupClassification,
    )

    ac, _, _ = client
    mock_result = HeartbeatEvDiscoveryResult(
        site_slug="akarp",
        site_name="Åkarp",
        system_id="sys-1",
        authenticated=True,
        ev_profiles=(),
        wallboxes=(),
        ems_devices=(),
        assignments=(),
        charging_modes=(),
        ai_decision_types=(),
        ai_decisions_found=False,
        resolved_ev_id=ResolvedEvId(None, 0.0, "none", None, ()),
        setup_classification=SetupClassification.EV_ID_NOT_FOUND,
        bridge_lifecycle=BridgeLifecycleState.DISCOVERY,
        halo_found=False,
        halo_online=False,
        virtual_bridge_suitable=False,
        warnings=(),
        observations=(),
        field_hints=(),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        report_text="test report",
    )

    with patch(
        "app.api.heartbeat_bridge.HeartbeatEvBridgeService.run_discovery",
        new=AsyncMock(return_value=(mock_result, 1)),
    ):
        response = await ac.post("/api/sites/akarp/heartbeat/discovery/run")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == 1
    assert data["report_text"] == "test report"


@pytest.mark.asyncio
async def test_bridge_settings_defaults(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/heartbeat/bridge/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["discovery_enabled"] is True
    assert data["write_enabled"] is False
    assert data["simulation_mode"] is True


@pytest.mark.asyncio
async def test_write_test_dry_run_requires_mapping(client):
    ac, _, _ = client
    response = await ac.post("/api/sites/akarp/heartbeat/write-test/run?dry_run=true")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bridge_decisions_empty(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/heartbeat/bridge/decisions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_bridge_status(client):
    ac, _, _ = client
    response = await ac.get("/api/sites/akarp/heartbeat/bridge/status")
    assert response.status_code == 200
    data = response.json()
    assert "heartbeat_connection" in data
    assert "Authorization" not in str(data)
