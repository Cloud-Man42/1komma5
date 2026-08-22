"""Tests for Open-Meteo response parsing."""

from __future__ import annotations

import pytest

from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider, WeatherProviderError
from energy_core.solar_forecast.types import SolarSiteConfiguration


def test_parse_minutely_15_response() -> None:
    provider = OpenMeteoWeatherProvider()
    data = {
        "minutely_15": {
            "time": ["2026-06-15T10:00", "2026-06-15T10:15"],
            "shortwave_radiation": [100.0, 200.0],
            "direct_radiation": [80.0, 160.0],
            "diffuse_radiation": [20.0, 40.0],
            "global_tilted_irradiance": [95.0, 190.0],
            "temperature_2m": [18.0, 19.0],
            "cloud_cover": [10.0, 20.0],
            "precipitation": [0.0, 0.0],
            "weather_code": [0, 1],
            "sunshine_duration": [600.0, 700.0],
        }
    }
    site = SolarSiteConfiguration(
        site_id=1, latitude=55.6, longitude=13.0, installed_peak_power_kw=8.0, enabled=True
    )
    forecast = provider._parse_response(site, data, provider="open-meteo")
    assert len(forecast.points) == 2
    assert forecast.points[0].gti_wm2 == 95.0


def test_missing_time_raises() -> None:
    provider = OpenMeteoWeatherProvider()
    with pytest.raises(WeatherProviderError):
        provider._parse_response(
            SolarSiteConfiguration(site_id=1, latitude=1, longitude=1, installed_peak_power_kw=1, enabled=True),
            {"minutely_15": {}},
            provider="open-meteo",
        )
