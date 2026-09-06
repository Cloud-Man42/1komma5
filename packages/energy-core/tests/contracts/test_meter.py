"""Meter helper contract tests."""

from datetime import UTC, datetime

from energy_core.contracts.devices.meter import (
    MeterSnapshot,
    integrate_power_kwh,
    session_energy_from_meter,
)
from energy_core.chargers.meter_adapter import (
    MeterSnapshot as ShimMeterSnapshot,
    integrate_power_kwh as shim_integrate,
    session_energy_from_meter as shim_session_energy,
)


def test_session_energy_from_meter_positive_delta() -> None:
    kwh, quality = session_energy_from_meter(10.0, 12.5)
    assert kwh == 2.5
    assert quality == "MEASURED"


def test_session_energy_from_meter_negative_delta_is_incomplete() -> None:
    kwh, quality = session_energy_from_meter(12.0, 10.0)
    assert kwh is None
    assert quality == "INCOMPLETE"


def test_integrate_power_kwh() -> None:
    assert integrate_power_kwh(2000.0, 0.5) == 1.0
    assert integrate_power_kwh(0.0, 1.0) == 0.0


def test_meter_snapshot_shim_reexport() -> None:
    snapshot = MeterSnapshot(
        recorded_at=datetime.now(UTC),
        cumulative_kwh=1.0,
        power_w=100.0,
        configured_current_a=10.0,
        actual_charging_current_a=9.0,
        is_charging=True,
        vehicle_connected=True,
        ocpp_status="Charging",
        phase_current_l1_a=None,
        phase_current_l2_a=None,
        phase_current_l3_a=None,
        energy_source="meter",
    )
    assert ShimMeterSnapshot is MeterSnapshot
    assert shim_integrate(1000.0, 1.0) == integrate_power_kwh(1000.0, 1.0)
    assert shim_session_energy(1.0, 2.0) == session_energy_from_meter(1.0, 2.0)
    assert snapshot.energy_source == "meter"
