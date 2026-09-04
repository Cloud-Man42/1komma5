"""Tests for Mercedes/Halo connection signal resolution."""

from __future__ import annotations

from energy_core.db.models import VehicleStateLatestModel
from energy_core.vehicles.connection_signals import (
    infer_plugged_in_from_mercedes,
    resolve_effective_connection,
)


def _latest(**kwargs) -> VehicleStateLatestModel:
    return VehicleStateLatestModel(vehicle_id=1, **kwargs)


def test_code_8_not_charging_infers_unplugged():
    assert (
        infer_plugged_in_from_mercedes(
            is_plugged_in=None,
            is_charging=False,
            charging_power_kw=0.0,
            charging_status_label="not_charging",
        )
        is False
    )


def test_explicit_plugged_stays_plugged_during_pause():
    assert (
        infer_plugged_in_from_mercedes(
            is_plugged_in=True,
            is_charging=False,
            charging_power_kw=0.0,
        )
        is True
    )


def test_halo_disconnected_keeps_explicit_mercedes_plugged():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=True, is_charging=False, charging_power_kw=0.0),
        halo_vehicle_connected=False,
    )
    assert effective.is_plugged_in is True
    assert effective.is_charging is False


def test_correlation_mismatch_closes_effective_connection():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=True, is_charging=False, charging_power_kw=0.0),
        plugged_agreement=False,
    )
    assert effective.is_plugged_in is False


def test_stale_power_does_not_clear_explicit_plug():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=True, is_charging=False, charging_power_kw=10.9),
    )
    assert effective.is_plugged_in is True
    assert effective.is_charging is False


def test_stale_charging_telemetry_assumes_charging_when_plugged():
    from datetime import UTC, datetime, timedelta

    effective = resolve_effective_connection(
        _latest(
            is_plugged_in=True,
            is_charging=False,
            charging_power_kw=10.9,
            charging_updated_at=datetime.now(UTC) - timedelta(hours=6),
        ),
    )
    assert effective.is_plugged_in is True
    assert effective.is_charging is True


def test_charge_break_keeps_plugged_without_power():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=True, is_charging=False, charging_power_kw=0.0),
    )
    assert effective.is_plugged_in is True


def test_stale_power_ignored_when_not_charging():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=None, is_charging=False, charging_power_kw=10.9),
    )
    assert effective.is_plugged_in is False
    assert effective.is_charging is False


def test_ambiguous_idle_without_halo_is_unplugged():
    effective = resolve_effective_connection(
        _latest(is_plugged_in=None, is_charging=False, charging_power_kw=0.0),
    )
    assert effective.is_plugged_in is False
