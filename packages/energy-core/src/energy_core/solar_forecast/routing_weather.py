"""Route weather requests to DMI (Denmark) or Open-Meteo."""

from __future__ import annotations

from datetime import datetime

from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecast
from energy_core.solar_forecast.weather import WeatherForecastProvider
from energy_core.solar_intelligence.provider_factory import resolve_country_code


class RoutingWeatherForecastProvider(WeatherForecastProvider):
    def __init__(
        self,
        *,
        open_meteo: WeatherForecastProvider,
        dmi: WeatherForecastProvider,
    ) -> None:
        self._open_meteo = open_meteo
        self._dmi = dmi

    async def get_forecast(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
    ) -> WeatherForecast:
        country = resolve_country_code(site.country_code, latitude=site.latitude, longitude=site.longitude)
        if country == "DK":
            return await self._dmi.get_forecast(site, from_ts, to_ts)
        return await self._open_meteo.get_forecast(site, from_ts, to_ts)
