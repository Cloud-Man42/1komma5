"""Tests for adaptive Mercedes polling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.vehicles.polling import AdaptivePollingPlanner, VehicleActivityMode


def test_charging_uses_short_interval():
    decision = AdaptivePollingPlanner().decide(is_charging=True, is_plugged_in=True, last_vehicle_update=datetime.now(UTC))
    assert decision.mode == VehicleActivityMode.CHARGING
    assert 30 <= decision.interval_seconds <= 60


def test_sleeping_uses_long_interval():
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=False,
        last_vehicle_update=datetime.now(UTC) - timedelta(minutes=20),
    )
    assert decision.mode == VehicleActivityMode.SLEEPING
    assert decision.interval_seconds >= 600
