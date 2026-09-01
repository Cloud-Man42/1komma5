"""Tests for vehicle list freshness helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.api.vehicles import _field_is_stale, _freshness_label, _guard_stale_connection_fields, _latest_signal_timestamp
from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.abstractions.models import DataQuality, VehicleConnectionState


def test_freshness_uses_latest_field_timestamp():
    latest = VehicleStateLatestModel(
        vehicle_id=1,
        connection_state=VehicleConnectionState.CONNECTED.value,
        data_quality=DataQuality.STALE.value,
        last_vehicle_update=datetime.now(UTC) - timedelta(minutes=20),
        charging_updated_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    signal = _latest_signal_timestamp(latest)
    label = _freshness_label(
        connection_state=latest.connection_state,
        data_quality=latest.data_quality,
        last_vehicle_update=signal,
    )
    assert label == "LIVE"


def test_guard_stale_keeps_recent_charging_last_known_good():
    is_plugged_in, is_charging, power = _guard_stale_connection_fields(
        "INAKTUELL",
        is_plugged_in=True,
        is_charging=True,
        charging_power_kw=10.9,
        charging_updated_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    assert is_plugged_in is True
    assert is_charging is True
    assert power == 10.9


def test_guard_stale_hides_old_charging_last_known_good():
    is_plugged_in, is_charging, power = _guard_stale_connection_fields(
        "INAKTUELL",
        is_plugged_in=True,
        is_charging=True,
        charging_power_kw=10.9,
        charging_updated_at=datetime.now(UTC) - timedelta(minutes=20),
    )
    assert is_plugged_in is None
    assert is_charging is None
    assert power is None


def test_field_is_stale_uses_soc_timestamp():
    assert _field_is_stale(datetime.now(UTC) - timedelta(minutes=20)) is True
    assert _field_is_stale(datetime.now(UTC) - timedelta(minutes=2)) is False
