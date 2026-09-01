"""ChargeFinder scoring integration tests."""

from energy_core.integrations.charging_stations.models import ChargingStationCandidate, StationProvider
from energy_core.vehicles.charging_intelligence.station_match import score_candidates


def test_known_location_and_operator_boosts_score():
    candidate = ChargingStationCandidate(
        provider=StationProvider.CHARGEFINDER,
        provider_station_id="hotel1",
        operator="ChargeNode",
        station_name="Hotel charger",
        latitude=59.3293,
        longitude=18.0686,
        distance_m=22,
        charging_type="AC",
        max_power_kw=11,
    )
    scored = score_candidates(
        [candidate],
        expected_operator="ChargeNode",
        geofence_match=True,
    )
    assert scored[0].score >= 80
