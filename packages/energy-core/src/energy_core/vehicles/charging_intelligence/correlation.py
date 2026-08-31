"""Multi-source charging correlation scoring."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.vehicles.charging_intelligence.location import ConfidenceBand, LocationMatch


@dataclass(frozen=True, slots=True)
class CorrelationSignals:
    geofence_match: bool = False
    charger_active: bool = False
    mercedes_charging: bool = False
    soc_increasing: bool = False
    house_load_matches: bool = False
    timestamps_match: bool = False


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    score: int
    confidence_band: ConfidenceBand
    identification_method: str


class ChargingCorrelationEngine:
    WEIGHTS = {
        "geofence_match": 40,
        "charger_active": 40,
        "mercedes_charging": 30,
        "soc_increasing": 20,
        "house_load_matches": 15,
        "timestamps_match": 20,
    }

    def score(self, signals: CorrelationSignals, *, location: LocationMatch | None = None) -> CorrelationResult:
        total = 0
        if signals.geofence_match:
            total += self.WEIGHTS["geofence_match"]
        if signals.charger_active:
            total += self.WEIGHTS["charger_active"]
        if signals.mercedes_charging:
            total += self.WEIGHTS["mercedes_charging"]
        if signals.soc_increasing:
            total += self.WEIGHTS["soc_increasing"]
        if signals.house_load_matches:
            total += self.WEIGHTS["house_load_matches"]
        if signals.timestamps_match:
            total += self.WEIGHTS["timestamps_match"]

        band = confidence_band(total)
        method = "UNKNOWN"
        if location is not None:
            method = location.identification_method.value
        if signals.charger_active and signals.mercedes_charging:
            method = "VEHICLE_AND_CHARGER_CORRELATION"
        elif signals.mercedes_charging:
            method = "MERCEDES_ONLY"
        elif signals.charger_active:
            method = "CHARGER_ONLY"
        return CorrelationResult(score=total, confidence_band=band, identification_method=method)


def confidence_band(score: int) -> ConfidenceBand:
    if score <= 30:
        return ConfidenceBand.UNKNOWN
    if score <= 60:
        return ConfidenceBand.LOW
    if score <= 80:
        return ConfidenceBand.MEDIUM
    if score <= 95:
        return ConfidenceBand.HIGH
    return ConfidenceBand.VERY_HIGH
