"""Tests for adaptive Mercedes polling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.vehicles.polling import AdaptivePollingPlanner, VehicleActivityMode


def test_charging_uses_moderate_interval():
    decision = AdaptivePollingPlanner().decide(is_charging=True, is_plugged_in=True, last_vehicle_update=datetime.now(UTC))
    assert decision.mode == VehicleActivityMode.CHARGING
    assert 90 <= decision.interval_seconds <= 120


def test_plugged_without_charging_uses_longer_interval():
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=True,
        last_vehicle_update=datetime.now(UTC),
    )
    assert decision.mode == VehicleActivityMode.PLUGGED
    assert 180 <= decision.interval_seconds <= 300


def test_stale_data_uses_recovery_interval():
    midday = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=False,
        last_vehicle_update=midday - timedelta(minutes=20),
        now=midday,
    )
    assert decision.mode == VehicleActivityMode.STALE_RECOVERY
    assert 180 <= decision.interval_seconds <= 300


def test_stale_soc_triggers_recovery_even_when_vehicle_update_is_recent():
    now = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    decision = AdaptivePollingPlanner().decide(
        is_charging=False,
        is_plugged_in=False,
        last_vehicle_update=now - timedelta(minutes=1),
        soc_updated_at=now - timedelta(minutes=20),
        now=now,
    )
    assert decision.mode == VehicleActivityMode.STALE_RECOVERY


def test_stale_power_does_not_trigger_charging_mode():
    decision = AdaptivePollingPlanner().decide(
        is_charging=None,
        is_plugged_in=True,
        charging_power_kw=10.9,
        charging_updated_at=datetime.now(UTC) - timedelta(minutes=20),
        last_vehicle_update=datetime.now(UTC),
    )
    assert decision.mode == VehicleActivityMode.PLUGGED


def test_fresh_power_infers_charging_mode():
    decision = AdaptivePollingPlanner().decide(
        is_charging=None,
        is_plugged_in=None,
        charging_power_kw=10.9,
        charging_updated_at=datetime.now(UTC) - timedelta(seconds=30),
        last_vehicle_update=datetime.now(UTC),
    )
    assert decision.mode == VehicleActivityMode.CHARGING
    assert 90 <= decision.interval_seconds <= 120


def test_position_recovery_when_away_charging_without_gps():
    decision = AdaptivePollingPlanner().decide(
        is_charging=True,
        is_plugged_in=True,
        charging_power_kw=10.9,
        charging_updated_at=datetime.now(UTC),
        last_vehicle_update=datetime.now(UTC),
        missing_gps=True,
        away_from_home=True,
    )
    assert decision.mode == VehicleActivityMode.POSITION_RECOVERY
    assert 60 <= decision.interval_seconds <= 90


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
