"""Tests for Heartbeat intent and constraints."""

from __future__ import annotations

import json
from pathlib import Path

from energy_core.heartbeat.bridge.constraints import BridgeConstraintResolver, BridgeConstraints, intent_to_halo_command
from energy_core.heartbeat.bridge.intent import HeartbeatIntentParser

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "heartbeat"


def test_intent_parser_smart_charge():
    ev = json.loads((FIXTURES / "ev_profiles.json").read_text())[0]
    parser = HeartbeatIntentParser()
    intent = parser.parse(ev_profile=ev, ems_settings=None, optimizations=[])
    assert intent.charging_mode == "SMART_CHARGE"
    assert intent.charge_requested is True


def test_intent_parser_unknown_mode():
    parser = HeartbeatIntentParser()
    intent = parser.parse(
        ev_profile={"chargeSettings": {"chargingMode": "MYSTERY_MODE"}},
        ems_settings=None,
        optimizations=[],
    )
    assert intent.charging_mode == "UNKNOWN: MYSTERY_MODE"


def test_constraint_resolver_blocks_below_minimum():
    parser = HeartbeatIntentParser()
    ev = json.loads((FIXTURES / "ev_profiles.json").read_text())[0]
    intent = parser.parse(ev_profile=ev, ems_settings=None, optimizations=[])
    resolver = BridgeConstraintResolver()
    resolved = resolver.resolve(
        intent,
        BridgeConstraints(
            heartbeat_requested_power_w=5000,
            solar_available_power_w=500,
            smart_charging_allowed_power_w=5000,
            load_balancer_allowed_power_w=5000,
            halo_hardware_limit_w=11000,
            vehicle_limit_w=11000,
            site_limit_w=11000,
        ),
    )
    assert resolved.blocked is True
    command = intent_to_halo_command(intent, resolved)
    assert command.action == "stop"


def test_ai_decision_ev_charge_from_grid():
    opts = json.loads((FIXTURES / "ai_optimizations.json").read_text())
    parser = HeartbeatIntentParser()
    intent = parser.parse(ev_profile=None, ems_settings=None, optimizations=opts)
    assert intent.charge_requested is True
    assert intent.raw_decision_type == "EV_CHARGE_FROM_GRID"
