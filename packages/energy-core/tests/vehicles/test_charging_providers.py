"""Tests for charging providers."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.charging_intelligence.providers import ManualChargingProvider, MercedesChargeProvider


def test_mercedes_provider_from_state():
    latest = VehicleStateLatestModel(
        vehicle_id=1,
        state_of_charge_percent=65.0,
        is_plugged_in=True,
        is_charging=True,
        charging_power_kw=11.0,
        connection_state="CONNECTED",
        data_quality="MEASURED",
        last_vehicle_update=datetime(2026, 8, 31, 12, 0, tzinfo=UTC),
    )
    snap = MercedesChargeProvider().snapshot_from_state(latest)
    assert snap.is_charging is True
    assert snap.charging_power_kw == 11.0
    assert snap.source == "MERCEDES"


def test_manual_provider():
    snap = ManualChargingProvider().snapshot(is_plugged_in=True, is_charging=True, charging_power_kw=22.0)
    assert snap.source == "MANUAL"
    assert snap.charging_power_kw == 22.0
