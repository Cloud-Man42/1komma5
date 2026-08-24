"""Tests for Heartbeat EV control helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from energy_core.heartbeat.ev_control import (
    build_charge_settings_patch,
    parse_ev_settings,
    settings_differ,
)


def test_build_charge_settings_patch_target_soc():
    payload = build_charge_settings_patch(target_soc_pct=80.0)
    assert payload == {"chargeSettings": {"targetSoc": 0.8}}


def test_build_charge_settings_patch_rejects_paused():
    with pytest.raises(ValueError, match="PAUSED"):
        build_charge_settings_patch(charging_mode="PAUSED")


def test_parse_ev_settings():
    remote = parse_ev_settings(
        {
            "updatedAt": "2026-08-24T10:00:00Z",
            "chargeSettings": {
                "chargingMode": "SMART_CHARGE",
                "targetSoc": 0.75,
                "primaryScheduleDepartureTime": "07:00",
            },
        }
    )
    assert remote.charging_mode == "SMART_CHARGE"
    assert remote.target_soc_pct == pytest.approx(75.0)
    assert remote.departure_time == "07:00"
    assert remote.remote_updated_at == datetime(2026, 8, 24, 10, 0, tzinfo=UTC)


def test_settings_differ_ignores_paused_local_mode():
    local = parse_ev_settings({"chargeSettings": {"chargingMode": "PAUSED", "targetSoc": 0.8}})
    remote = parse_ev_settings({"chargeSettings": {"chargingMode": "SMART_CHARGE", "targetSoc": 0.8}})
    assert settings_differ(local, remote)
