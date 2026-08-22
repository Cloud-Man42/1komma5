"""Azimuth conversion between EMIC and Open-Meteo conventions."""

from __future__ import annotations


def emic_azimuth_to_open_meteo(azimuth_deg: float) -> float:
    """Convert EMIC azimuth (180°=south, 90°=east, 270°=west) to Open-Meteo (0°=south)."""
    value = azimuth_deg - 180.0
    if value > 180.0:
        value -= 360.0
    if value < -180.0:
        value += 360.0
    return value


def open_meteo_azimuth_to_emic(azimuth_deg: float) -> float:
    """Convert Open-Meteo azimuth to EMIC convention."""
    value = azimuth_deg + 180.0
    if value >= 360.0:
        value -= 360.0
    if value < 0.0:
        value += 360.0
    return value
