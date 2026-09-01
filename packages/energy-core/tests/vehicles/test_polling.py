"""Tests for adaptive Mercedes polling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.vehicles.polling import AdaptivePollingPlanner, VehicleActivityMode


def test_charging_uses_short_interval():
    decision = AdaptivePollingPlanner().decide(is_charging=True, is_plugged_in=True, last_vehicle_update=datetime.now(UTC))
    assert decision.mode == VehicleActivityMode.CHARGING
    assert 30 <= decision.interval_seconds <= 60


def test_stale_data_uses_recovery_interval():
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=False,
        last_vehicle_update=datetime.now(UTC) - timedelta(minutes=20),
    )
    assert decision.mode == VehicleActivityMode.STALE_RECOVERY
    assert 60 <= decision.interval_seconds <= 120


def test_stale_soc_triggers_recovery_even_when_vehicle_update_is_recent():
    now = datetime.now(UTC)
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=False,
        last_vehicle_update=now - timedelta(minutes=1),
        soc_updated_at=now - timedelta(minutes=20),
    )
    assert decision.mode == VehicleActivityMode.STALE_RECOVERY


def test_charging_inferred_from_power_when_plug_flags_missing():
    decision = AdaptivePollingPlanner().decide(
        is_charging=None,
        is_plugged_in=None,
        charging_power_kw=10.9,
        last_vehicle_update=datetime.now(UTC) - timedelta(minutes=20),
    )
    assert decision.mode == VehicleActivityMode.CHARGING
    assert 30 <= decision.interval_seconds <= 60


def test_position_recovery_when_away_charging_without_gps():
    decision = AdaptivePollingPlanner().decide(
        is_charging=True,
        is_plugged_in=True,
        charging_power_kw=10.9,
        last_vehicle_update=datetime.now(UTC),
        missing_gps=True,
        away_from_home=True,
    )
    assert decision.mode == VehicleActivityMode.POSITION_RECOVERY
    assert decision.interval_seconds == 30


def test_position_recovery_not_when_gps_present():
    decision = AdaptivePollingPlanner().decide(
        is_charging=True,
        is_plugged_in=True,
        missing_gps=False,
        away_from_home=True,
        last_vehicle_update=datetime.now(UTC),
    )
    assert decision.mode == VehicleActivityMode.CHARGING


def test_position_recovery_not_when_at_home():
    decision = AdaptivePollingPlanner().decide(
        is_charging=True,
        is_plugged_in=True,
        missing_gps=True,
        away_from_home=False,
        last_vehicle_update=datetime.now(UTC),
    )
    assert decision.mode == VehicleActivityMode.CHARGING
