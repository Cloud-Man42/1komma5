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
    CHARGEFINDER = "CHARGEFINDER"
    CHARGEFINDER_AND_GEOFENCE = "CHARGEFINDER_AND_GEOFENCE"
    KNOWN_STATION = "KNOWN_STATION"
    MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
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


AWAY_LOCATION_NAME = "Borta (ej hemma)"


@dataclass(frozen=True, slots=True)
class HaloCorrelationHint:
    status: str | None = None
    plugged_agreement: bool | None = None


class ChargingLocationResolver:
    def __init__(self, locations: list[ChargingLocationDefinition]) -> None:
        self._locations = locations

    def resolve(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        halo: HaloCorrelationHint | None = None,
        mercedes_plugged: bool | None = None,
        mercedes_charging: bool | None = None,
        mercedes_power_kw: float | None = None,
        halo_charger_active: bool | None = None,
    ) -> LocationMatch:
        if latitude is None or longitude is None:
            away = infer_away_from_home(
                halo=halo,
                mercedes_plugged=mercedes_plugged,
                mercedes_charging=mercedes_charging,
                mercedes_power_kw=mercedes_power_kw,
                halo_charger_active=halo_charger_active,
            )
            if away is not None:
                return away
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


def infer_away_from_home(
    *,
    halo: HaloCorrelationHint | None,
    mercedes_plugged: bool | None,
    mercedes_charging: bool | None,
    mercedes_power_kw: float | None = None,
    halo_charger_active: bool | None = None,
) -> LocationMatch | None:
    """Infer away-from-home charging when Mercedes reports activity but Halo at home does not."""
    charging = mercedes_charging
    plugged = mercedes_plugged
    if charging is None and mercedes_power_kw is not None and mercedes_power_kw >= 0.3:
        charging = True
    if plugged is None and charging:
        plugged = True
    if not (plugged or charging):
        return None
    if halo is not None and halo.status == "MISMATCH":
        return _away_match()
    if halo_charger_active is False:
        return _away_match()
    return None


def is_away_charging(
    *,
    halo: HaloCorrelationHint | None,
    mercedes_plugged: bool | None,
    mercedes_charging: bool | None,
    mercedes_power_kw: float | None = None,
    halo_charger_active: bool | None = None,
) -> bool:
    return infer_away_from_home(
        halo=halo,
        mercedes_plugged=mercedes_plugged,
        mercedes_charging=mercedes_charging,
        mercedes_power_kw=mercedes_power_kw,
        halo_charger_active=halo_charger_active,
    ) is not None


def _away_match() -> LocationMatch:
    return LocationMatch(
        location=None,
        location_name=AWAY_LOCATION_NAME,
        charger_operator=None,
        charger_network=None,
        home_charging=False,
        identification_method=IdentificationMethod.MERCEDES_ONLY,
        confidence_band=ConfidenceBand.MEDIUM,
        confidence_score=55,
    )

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))
