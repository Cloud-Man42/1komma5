"""Tests for shared Charge Amps vehicle connection heuristics."""

from energy_core.chargers.vehicle_status import (
    vehicle_connected_from_external_connector,
    vehicle_connected_from_web_connector,
)


def test_web_connector_detects_preparing():
    assert vehicle_connected_from_web_connector({"ocppStatus": "Preparing"}) is True


def test_web_connector_detects_is_charging_flag():
    assert (
        vehicle_connected_from_web_connector({"ocppStatus": "Available", "isCharging": True})
        is True
    )


def test_external_connector_detects_ev_connected_flag():
    assert (
        vehicle_connected_from_external_connector({"status": "Available", "evConnected": True})
        is True
    )


def test_external_connector_ignores_available_without_signals():
    assert vehicle_connected_from_external_connector({"status": "Available"}) is False


def test_web_connector_detects_voltage_presence():
    assert (
        vehicle_connected_from_web_connector({"ocppStatus": "Unavailable", "voltage1": 230.0})
        is True
    )
