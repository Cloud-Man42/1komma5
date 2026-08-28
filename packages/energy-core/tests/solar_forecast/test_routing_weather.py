"""Tests for country-routed weather providers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from energy_core.solar_forecast.routing_weather import RoutingWeatherForecastProvider
from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecast


class _StubProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    async def get_forecast(self, site, from_ts, to_ts):
        self.calls += 1
        return WeatherForecast(
            site_id=site.site_id,
            fetched_at=datetime.now(UTC),
            provider=self.name,
            points=(),
        )


@pytest.mark.asyncio
async def test_routing_weather_uses_dmi_for_denmark():
    open_meteo = _StubProvider("open-meteo")
    dmi = _StubProvider("dmi-harmonie")
    router = RoutingWeatherForecastProvider(open_meteo=open_meteo, dmi=dmi)
    site = SolarSiteConfiguration(
        site_id=2,
        latitude=55.715,
        longitude=12.561,
        installed_peak_power_kw=8.0,
        enabled=True,
        country_code="DK",
    )
    now = datetime.now(UTC)
    forecast = await router.get_forecast(site, now, now)
    assert forecast.provider == "dmi-harmonie"
    assert dmi.calls == 1
    assert open_meteo.calls == 0


@pytest.mark.asyncio
async def test_routing_weather_uses_open_meteo_for_sweden():
    open_meteo = _StubProvider("open-meteo")
    dmi = _StubProvider("dmi-harmonie")
    router = RoutingWeatherForecastProvider(open_meteo=open_meteo, dmi=dmi)
    site = SolarSiteConfiguration(
        site_id=1,
        latitude=59.3,
        longitude=18.0,
        installed_peak_power_kw=10.0,
        enabled=True,
        country_code="SE",
    )
    now = datetime.now(UTC)
    forecast = await router.get_forecast(site, now, now)
    assert forecast.provider == "open-meteo"
    assert open_meteo.calls == 1
    assert dmi.calls == 0
