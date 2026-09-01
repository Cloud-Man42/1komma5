"""Tests for charging correlation and location intelligence."""

from __future__ import annotations

from energy_core.vehicles.charging_intelligence.correlation import ChargingCorrelationEngine, CorrelationSignals, confidence_band
from energy_core.vehicles.charging_intelligence.location import (
    AWAY_LOCATION_NAME,
    ChargingLocationDefinition,
    ChargingLocationResolver,
    ConfidenceBand,
    HaloCorrelationHint,
    LocationClassification,
    infer_away_from_home,
    is_away_charging,
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


def test_infer_away_from_home_when_halo_mismatch():
    match = infer_away_from_home(
        halo=HaloCorrelationHint(status="MISMATCH", plugged_agreement=False),
        mercedes_plugged=True,
        mercedes_charging=True,
    )
    assert match is not None
    assert match.location_name == AWAY_LOCATION_NAME
    assert match.home_charging is False
    assert match.confidence_band == ConfidenceBand.MEDIUM


def test_infer_away_requires_mismatch():
    assert infer_away_from_home(
        halo=HaloCorrelationHint(status="ALIGNED", plugged_agreement=True),
        mercedes_plugged=True,
        mercedes_charging=True,
    ) is None


def test_resolver_away_without_gps():
    resolver = ChargingLocationResolver([])
    match = resolver.resolve(
        latitude=None,
        longitude=None,
        halo=HaloCorrelationHint(status="MISMATCH", plugged_agreement=False),
        mercedes_plugged=True,
        mercedes_charging=True,
    )
    assert match.location_name == AWAY_LOCATION_NAME
    assert is_away_charging(
        halo=HaloCorrelationHint(status="MISMATCH"),
        mercedes_plugged=True,
        mercedes_charging=False,
    )


def test_infer_away_when_mercedes_power_but_halo_idle():
    match = infer_away_from_home(
        halo=HaloCorrelationHint(status="UNAVAILABLE"),
        mercedes_plugged=None,
        mercedes_charging=None,
        mercedes_power_kw=10.9,
        halo_charger_active=False,
    )
    assert match is not None
    assert match.location_name == AWAY_LOCATION_NAME


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
