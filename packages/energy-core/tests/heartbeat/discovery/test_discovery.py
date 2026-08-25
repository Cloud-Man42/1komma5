"""Tests for Heartbeat EV discovery."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from energy_core.heartbeat.discovery.confidence import resolve_best_ev_id
from energy_core.heartbeat.discovery.classification import classify_setup
from energy_core.heartbeat.discovery.models import SetupClassification
from energy_core.heartbeat.discovery.report import _next_step, generate_discovery_report
from energy_core.heartbeat.discovery.service import (
    HeartbeatEvDiscoveryService,
    _parse_ev_profile,
    _parse_wallbox,
)
from energy_core.heartbeat.discovery.redaction import contains_credential_leak, redact_headers

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "heartbeat"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_redact_headers_masks_authorization():
    headers = {"Authorization": "Bearer secret-token", "Accept": "application/json"}
    redacted = redact_headers(headers)
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["Accept"] == "application/json"


def test_contains_credential_leak_detects_bearer():
    assert contains_credential_leak('{"Authorization": "Bearer abc"}')


def test_parse_ev_profile_mercedes_eqe():
    ev = _load("ev_profiles.json")[0]
    profile = _parse_ev_profile(ev)
    assert profile.manufacturer == "Mercedes-Benz"
    assert profile.model == "EQE 500"
    assert profile.charging_mode == "SMART_CHARGE"
    assert profile.current_soc_pct == pytest.approx(72.0)


def test_resolve_single_ev_without_wallbox():
    ev = _load("ev_profiles.json")[0]
    profile = _parse_ev_profile(ev)
    resolved = resolve_best_ev_id((profile,), (), ())
    assert resolved.confidence_pct == 95.0
    assert resolved.heartbeat_ev_id == ev["id"]


def test_classify_virtual_bridge_candidate():
    ev = _load("ev_profiles.json")[0]
    profile = _parse_ev_profile(ev)
    resolved = resolve_best_ev_id((profile,), (), ())
    classification, lifecycle, suitable = classify_setup(
        authenticated=True,
        ev_profiles=(profile,),
        wallboxes=(),
        resolved=resolved,
        halo_found=True,
    )
    assert classification == SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY
    assert suitable is True


def test_classify_auth_failed():
    resolved = resolve_best_ev_id((), (), ())
    classification, _, _ = classify_setup(
        authenticated=False,
        ev_profiles=(),
        wallboxes=(),
        resolved=resolved,
        halo_found=False,
    )
    assert classification == SetupClassification.HEARTBEAT_AUTH_FAILED


@pytest.mark.asyncio
async def test_discovery_service_with_mock_client():
    evs = _load("ev_profiles.json")
    boxes = _load("wallboxes_empty.json")
    ems = _load("ems_settings.json")
    opts = _load("ai_optimizations.json")
    overview = _load("live_overview.json")

    client = MagicMock()
    client.list_evs = AsyncMock(return_value=evs)
    client.list_wallboxes = AsyncMock(return_value=boxes)
    client.fetch_ems_settings = AsyncMock(return_value=ems)
    client.list_charging_modes = AsyncMock(return_value=["SMART_CHARGE", "SOLAR_CHARGE"])
    client.fetch_optimizations = AsyncMock(return_value=opts)
    client.fetch_live_overview = AsyncMock(return_value=overview)

    service = HeartbeatEvDiscoveryService()
    result = await service.run(
        client=client,
        site_slug="akarp",
        site_name="Åkarp",
        system_id="test-system-id",
        halo_found=True,
        halo_online=True,
    )

    assert result.authenticated is True
    assert len(result.ev_profiles) == 1
    assert result.wallboxes == ()
    assert result.setup_classification == SetupClassification.VIRTUAL_CHARGER_BRIDGE_READY
    assert "EMIC HEARTBEAT EV DISCOVERY RESULT" in result.report_text
    assert result.ai_decisions_found is True
    assert "EV_CHARGE_FROM_GRID" in result.ai_decision_types


@pytest.mark.asyncio
async def test_discovery_no_system_id():
    service = HeartbeatEvDiscoveryService()
    client = MagicMock()
    result = await service.run(
        client=client,
        site_slug="akarp",
        site_name="Åkarp",
        system_id=None,
    )
    assert "no Heartbeat system ID" in result.warnings[0]


def test_parse_wallbox_assignment():
    box = _load("wallboxes_with_assignment.json")[0]
    parsed = _parse_wallbox(box)
    assert parsed.assigned_ev_id == "72903b13-aaaa-bbbb-cccc-ddddeeeeffff"


def test_next_step_ev_id_not_found():
    resolved = resolve_best_ev_id((), (), ())
    classification, lifecycle, suitable = classify_setup(
        authenticated=True,
        ev_profiles=(),
        wallboxes=(),
        resolved=resolved,
        halo_found=True,
    )
    from energy_core.heartbeat.discovery.models import HeartbeatEvDiscoveryResult

    result = HeartbeatEvDiscoveryResult(
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
        resolved_ev_id=resolved,
        setup_classification=classification,
        bridge_lifecycle=lifecycle,
        halo_found=True,
        halo_online=True,
        virtual_bridge_suitable=suitable,
        warnings=(),
        observations=(),
        field_hints=(),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    assert classification == SetupClassification.EV_ID_NOT_FOUND
    step = _next_step(result)
    assert "Heartbeat app" in step
    assert "Mercedes EQE" in step
    report = generate_discovery_report(result)
    assert "Register the vehicle in the Heartbeat app" in report
