"""Tests for meter adapter and session energy."""

from energy_core.chargers.meter_adapter import (
    _power_from_phases,
    integrate_power_kwh,
    session_energy_from_meter,
)


def test_session_energy_from_meter_delta():
    kwh, quality = session_energy_from_meter(100.0, 122.4)
    assert kwh == 22.4
    assert quality == "MEASURED"


def test_power_integration():
    assert integrate_power_kwh(11000, 1.0) == 11.0


def test_power_from_three_phases():
    power = _power_from_phases(10.0, 10.0, 10.0, 230.0, 3)
    assert power == 6900.0
