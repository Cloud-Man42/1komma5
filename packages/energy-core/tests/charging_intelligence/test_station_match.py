"""Tests for station candidate scoring."""

from __future__ import annotations

from energy_core.integrations.charging_stations.models import ChargingStationCandidate, StationProvider
from energy_core.vehicles.charging_intelligence.location import IdentificationMethod
from energy_core.vehicles.charging_intelligence.station_match import resolve_from_scores, score_candidates


def _candidate(station_id: str, operator: str, distance: float, *, confirmed: bool = False) -> ChargingStationCandidate:
    return ChargingStationCandidate(
        provider=StationProvider.CHARGEFINDER,
        provider_station_id=station_id,
        operator=operator,
        station_name=f"Station {station_id}",
        latitude=57.26,
        longitude=16.48,
        distance_m=distance,
        charging_type="AC",
        max_power_kw=22.0,
    )


def test_user_confirmed_gets_high_score():
    candidate = _candidate("A", "ChargeNode", 30)
    scored = score_candidates([candidate], user_confirmed_ids={"A"})
    assert scored[0].score >= 40


def test_operator_match_adds_points():
    candidate = _candidate("A", "ChargeNode", 30)
    scored = score_candidates([candidate], expected_operator="ChargeNode")
    assert scored[0].score >= 25


def test_multi_match_when_close_scores():
    first = _candidate("A", "OpA", 20)
    second = _candidate("B", "OpB", 25)
    scored = score_candidates([first, second])
    resolved = resolve_from_scores(
        scored,
        location_name="Away",
        identification_method=IdentificationMethod.CHARGEFINDER.value,
        source="CHARGEFINDER",
    )
    assert resolved.station_resolution_status.value == "MULTIPLE_CANDIDATES"
    assert resolved.identification_method == IdentificationMethod.MULTIPLE_CANDIDATES.value


def test_clear_winner_auto_selects():
    near = _candidate("A", "ChargeNode", 10)
    far = _candidate("B", "Other", 120)
    scored = score_candidates([near, far], expected_operator="ChargeNode")
    resolved = resolve_from_scores(
        scored,
        location_name="Away",
        identification_method=IdentificationMethod.CHARGEFINDER.value,
        source="CHARGEFINDER",
    )
    assert resolved.selected_station is not None
    assert resolved.station_resolution_status.value == "OK"
