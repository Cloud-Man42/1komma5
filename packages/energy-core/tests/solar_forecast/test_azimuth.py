"""Tests for solar forecast azimuth conversion."""

from energy_core.solar_forecast.azimuth import (
    emic_azimuth_to_open_meteo,
    open_meteo_azimuth_to_emic,
)


def test_south_facing_conversion() -> None:
    assert emic_azimuth_to_open_meteo(180.0) == 0.0


def test_east_facing_conversion() -> None:
    assert emic_azimuth_to_open_meteo(90.0) == -90.0


def test_roundtrip() -> None:
    for emic in (180.0, 90.0, 270.0, 0.0):
        assert open_meteo_azimuth_to_emic(emic_azimuth_to_open_meteo(emic)) == emic
