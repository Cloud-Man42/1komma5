"""Radiation source confidence and forecast quality."""

from __future__ import annotations

from energy_core.solar_intelligence.types import RadiationSourceConfidence


def radiation_confidence_for_location(*, latitude: float, longitude: float, provider: str) -> RadiationSourceConfidence:
    if provider == "open-meteo":
        return RadiationSourceConfidence.LOW
    if provider != "smhi-strang":
        return RadiationSourceConfidence.UNKNOWN

    # STRÅNG primary coverage: Sweden; Denmark allowed at MEDIUM
    if 55.0 <= latitude <= 69.5 and 10.5 <= longitude <= 24.5:
        if latitude >= 57.5 or longitude <= 13.0:
            return RadiationSourceConfidence.HIGH
        # Southern Denmark / Skåne edge
        return RadiationSourceConfidence.MEDIUM
    return RadiationSourceConfidence.MEDIUM


def confidence_score_from_metrics(*, wape: float | None, sample_count: int, radiation: RadiationSourceConfidence) -> float:
    base = 50.0
    if wape is not None:
        base = max(0.0, 100.0 - wape * 2.0)
    sample_bonus = min(20.0, sample_count / 3.0)
    rad_bonus = {
        RadiationSourceConfidence.HIGH: 15.0,
        RadiationSourceConfidence.MEDIUM: 8.0,
        RadiationSourceConfidence.LOW: 0.0,
        RadiationSourceConfidence.UNKNOWN: 0.0,
    }[radiation]
    return round(min(100.0, base + sample_bonus + rad_bonus), 1)
