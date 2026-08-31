"""Geofence-based charging location resolution."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class LocationClassification(StrEnum):
    HOME = "HOME"
    HOME_SECONDARY = "HOME_SECONDARY"
    WORK = "WORK"
    HOTEL = "HOTEL"
    PUBLIC = "PUBLIC"
    UNKNOWN = "UNKNOWN"


class IdentificationMethod(StrEnum):
    GEOFENCE = "GEOFENCE"
    VEHICLE_AND_CHARGER_CORRELATION = "VEHICLE_AND_CHARGER_CORRELATION"
    CHARGER_ONLY = "CHARGER_ONLY"
    MERCEDES_ONLY = "MERCEDES_ONLY"
    MANUAL = "MANUAL"
    UNKNOWN = "UNKNOWN"


class ConfidenceBand(StrEnum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass(frozen=True, slots=True)
class ChargingLocationDefinition:
    id: int | None
    name: str
    classification: LocationClassification
    latitude: float
    longitude: float
    radius_m: int
    expected_operator: str | None = None
    expected_network: str | None = None
    expected_charging_type: str | None = None
    charger_id: int | None = None
    price_model: str = "UNKNOWN"
    price_value: float | None = None


@dataclass(frozen=True, slots=True)
class LocationMatch:
    location: ChargingLocationDefinition | None
    location_name: str
    charger_operator: str | None
    charger_network: str | None
    home_charging: bool | None
    identification_method: IdentificationMethod
    confidence_band: ConfidenceBand
    confidence_score: int


class ChargingLocationResolver:
    def __init__(self, locations: list[ChargingLocationDefinition]) -> None:
        self._locations = locations

    def resolve(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
    ) -> LocationMatch:
        if latitude is None or longitude is None:
            return LocationMatch(
                location=None,
                location_name="Unknown",
                charger_operator=None,
                charger_network=None,
                home_charging=None,
                identification_method=IdentificationMethod.UNKNOWN,
                confidence_band=ConfidenceBand.UNKNOWN,
                confidence_score=0,
            )
        best: ChargingLocationDefinition | None = None
        best_distance = float("inf")
        for location in self._locations:
            distance = haversine_m(latitude, longitude, location.latitude, location.longitude)
            if distance <= location.radius_m and distance < best_distance:
                best = location
                best_distance = distance
        if best is None:
            return LocationMatch(
                location=None,
                location_name="Unknown",
                charger_operator=None,
                charger_network=None,
                home_charging=False,
                identification_method=IdentificationMethod.UNKNOWN,
                confidence_band=ConfidenceBand.UNKNOWN,
                confidence_score=0,
            )
        home = best.classification in {LocationClassification.HOME, LocationClassification.HOME_SECONDARY}
        return LocationMatch(
            location=best,
            location_name=best.name,
            charger_operator=best.expected_operator,
            charger_network=best.expected_network,
            home_charging=home,
            identification_method=IdentificationMethod.GEOFENCE,
            confidence_band=ConfidenceBand.HIGH,
            confidence_score=85,
        )


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
