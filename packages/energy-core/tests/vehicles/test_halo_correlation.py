"""Tests for Mercedes/Halo correlation."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.vehicles.abstractions.models import DataQuality, VehicleCapabilities, VehicleConnectionState, VehicleState
from energy_core.vehicles.correlation.halo import CorrelationStatus, HaloChargerSnapshot, correlate_vehicle_with_halo


def _vehicle(**kwargs) -> VehicleState:
    defaults = dict(
        vehicle_id="eqe-1",
        provider="mercedes",
        manufacturer="Mercedes-Benz",
        model="EQE 500",
        is_plugged_in=True,
        is_charging=True,
        charging_power_kw=7.2,
        data_quality=DataQuality.MEASURED,
        connection_state=VehicleConnectionState.CONNECTED,
        capabilities=VehicleCapabilities(),
    )
    defaults.update(kwargs)
    return VehicleState(**defaults)


def test_correlation_aligned_when_signals_match():
    result = correlate_vehicle_with_halo(
        _vehicle(),
        HaloChargerSnapshot(
            charger_id=1,
            vehicle_connected=True,
            is_charging=True,
            power_kw=7.0,
            updated_at=datetime.now(UTC),
        ),
    )
    assert result.status == CorrelationStatus.ALIGNED
    assert result.confidence >= 0.75
    assert result.plugged_agreement is True
    assert result.charging_agreement is True


def test_correlation_mismatch_when_plugged_state_differs():
    result = correlate_vehicle_with_halo(
        _vehicle(is_plugged_in=True, is_charging=False, charging_power_kw=0.0),
        HaloChargerSnapshot(
            charger_id=1,
            vehicle_connected=False,
            is_charging=False,
            power_kw=0.0,
            updated_at=datetime.now(UTC),
        ),
    )
    assert result.plugged_agreement is False
    assert result.status in {CorrelationStatus.MISMATCH, CorrelationStatus.PARTIAL}


def test_correlation_unavailable_without_halo():
    result = correlate_vehicle_with_halo(_vehicle(), None)
    assert result.status == CorrelationStatus.UNAVAILABLE
    assert result.confidence == 0.0
