"""Tests for charging correlation and location intelligence."""

from __future__ import annotations

from energy_core.vehicles.charging_intelligence.correlation import ChargingCorrelationEngine, CorrelationSignals, confidence_band
from energy_core.vehicles.charging_intelligence.location import (
    ChargingLocationDefinition,
    ChargingLocationResolver,
    ConfidenceBand,
    LocationClassification,
)


def test_geofence_match_akarp():
    resolver = ChargingLocationResolver(
        [
            ChargingLocationDefinition(
                id=1,
                name="Home Åkarp",
                classification=LocationClassification.HOME,
                latitude=55.61,
                longitude=13.12,
                radius_m=100,
                expected_operator="Charge Amps Halo",
                expected_charging_type="AC",
            )
        ]
    )
    match = resolver.resolve(latitude=55.6105, longitude=13.1205)
    assert match.location_name == "Home Åkarp"
    assert match.confidence_band == ConfidenceBand.HIGH


def test_correlation_vehicle_and_charger_very_high():
    result = ChargingCorrelationEngine().score(
        CorrelationSignals(
            geofence_match=True,
            charger_active=True,
            mercedes_charging=True,
            soc_increasing=True,
            timestamps_match=True,
        )
    )
    assert result.score >= 96
    assert confidence_band(result.score).value == "VERY_HIGH"


def test_state_machine_restore():
    from energy_core.vehicles.charging_intelligence.state_machine import ChargingState, VehicleChargingStateMachine

    sm = VehicleChargingStateMachine()
    sm.restore(ChargingState.CHARGING.value)
    assert sm.state == ChargingState.CHARGING
