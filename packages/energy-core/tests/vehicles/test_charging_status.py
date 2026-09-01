"""Tests for Mercedes chargingstatus enum decoding."""

from __future__ import annotations

from energy_core.vehicles.mercedes.charging_status import interpret_charging_status


def test_charging_status_code_8_means_not_charging_not_plugged_in():
    status = interpret_charging_status(8)
    assert status is not None
    assert status.label == "not_charging"
    assert status.is_charging is False
    assert status.is_plugged_in is None


def test_charging_status_code_3_means_unplugged():
    status = interpret_charging_status(3)
    assert status is not None
    assert status.is_plugged_in is False
    assert status.is_charging is False


def test_charging_status_accepts_string_aliases():
    status = interpret_charging_status("Unplugged")
    assert status is not None
    assert status.is_plugged_in is False
