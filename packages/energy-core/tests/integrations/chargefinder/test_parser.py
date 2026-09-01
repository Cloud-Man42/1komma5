"""Tests for ChargeFinder parser."""

from energy_core.integrations.charging_stations.chargefinder.parser import parse_station, parse_stations
from energy_core.integrations.charging_stations.models import StationProvider


def _sample_station(**overrides):
    payload = {
        "slug": "abc123",
        "title": "Hotel Charger",
        "operator": "ChargeNode",
        "location": {"latitude": 59.3293, "longitude": 18.0686},
        "locationAddress": {
            "city": "Stockholm",
            "countryCode": "SE",
            "full": "Hotel Street 1, Stockholm, Sweden",
        },
        "maxCapacity": 11,
        "outletList": [
            {
                "capacity": 11,
                "acdc": "AC",
                "outlets": [{"plug": "Type 2", "capacity": 11, "acdc": "AC3"}],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_parse_station_maps_chargefinder_fields():
    candidate = parse_station(_sample_station(), vehicle_lat=59.3293, vehicle_lon=18.0686)
    assert candidate is not None
    assert candidate.provider == StationProvider.CHARGEFINDER
    assert candidate.provider_station_id == "abc123"
    assert candidate.operator == "ChargeNode"
    assert candidate.connector_type == "Type 2"
    assert candidate.max_power_kw == 11
    assert candidate.charging_type == "AC"
    assert candidate.external_url.endswith("/abc123")


def test_parse_stations_filters_by_radius():
    far = _sample_station(slug="far", location={"latitude": 60.0, "longitude": 19.0})
    near = _sample_station(slug="near")
    candidates = parse_stations([far, near], vehicle_lat=59.3293, vehicle_lon=18.0686, radius_m=150)
    assert len(candidates) == 1
    assert candidates[0].provider_station_id == "near"


def test_parse_station_missing_slug_returns_none():
    assert parse_station({"title": "No slug"}, vehicle_lat=1, vehicle_lon=1) is None
