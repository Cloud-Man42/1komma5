"""Country-aware solar intelligence provider selection."""

from __future__ import annotations

from dataclasses import dataclass

from energy_core.config import Settings
from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_intelligence.engine import SolarIntelligenceEngine
from energy_core.solar_intelligence.providers.dmi_harmonie import (
    DmiHarmonieClient,
    DmiHarmonieRadiationProvider,
    DmiHarmonieWeatherProvider,
)
from energy_core.solar_intelligence.providers.open_meteo_adapter import OpenMeteoAdapter
from energy_core.solar_intelligence.providers.smhi_snow import SmhiSnowWeatherProvider
from energy_core.solar_intelligence.providers.smhi_strang import SmhiStrangRadiationProvider


def resolve_country_code(
    country_code: str | None,
    *,
    latitude: float,
    longitude: float,
) -> str:
    if country_code:
        return country_code.strip().upper()
    if 54.56 <= latitude <= 55.06 and 14.6 <= longitude <= 15.2:
        return "DK"
    if 54.4 <= latitude <= 57.8 and 7.5 <= longitude <= 12.75:
        return "DK"
    if 55.0 <= latitude <= 69.5 and 10.5 <= longitude <= 24.5:
        return "SE"
    return "OTHER"


@dataclass(frozen=True, slots=True)
class IntelligenceProviderBundle:
    country_code: str
    radiation_provider: object
    weather_provider: object
    radiation_name: str
    weather_name: str
    engine: SolarIntelligenceEngine


class SolarIntelligenceProviderFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        open_meteo = OpenMeteoWeatherProvider(
            base_url=settings.open_meteo_base_url,
            historical_url=settings.open_meteo_historical_url,
            api_key=settings.open_meteo_api_key or None,
            timeout_seconds=settings.open_meteo_timeout_seconds,
        )
        self._fallback = OpenMeteoAdapter(open_meteo)
        self._strang = SmhiStrangRadiationProvider(
            base_url=settings.smhi_strang_base_url,
            timeout_seconds=settings.smhi_timeout_seconds,
        )
        self._snow = SmhiSnowWeatherProvider(
            base_url=settings.smhi_snow_base_url,
            timeout_seconds=settings.smhi_timeout_seconds,
        )
        self._dmi_client = DmiHarmonieClient(
            base_url=settings.dmi_edr_base_url,
            collection=settings.dmi_harmonie_collection,
            timeout_seconds=settings.dmi_timeout_seconds,
        )
        self._dmi_radiation = DmiHarmonieRadiationProvider(self._dmi_client)
        self._dmi_weather = DmiHarmonieWeatherProvider(self._dmi_client)
        self._bundles: dict[str, IntelligenceProviderBundle] = {}

    @property
    def open_meteo_fallback(self) -> OpenMeteoAdapter:
        return self._fallback

    def bundle_for(self, *, country_code: str | None, latitude: float, longitude: float) -> IntelligenceProviderBundle:
        country = resolve_country_code(country_code, latitude=latitude, longitude=longitude)
        cached = self._bundles.get(country)
        if cached is not None:
            return cached

        if country == "DK":
            radiation = self._dmi_radiation
            weather = self._dmi_weather
            radiation_name = radiation.provider_name
            weather_name = weather.provider_name
        else:
            radiation = self._strang
            weather = self._snow
            radiation_name = radiation.provider_name
            weather_name = weather.provider_name

        engine = SolarIntelligenceEngine(
            radiation_provider=radiation,
            weather_provider=weather,
            open_meteo_fallback=self._fallback,
            horizon_hours=self._settings.solar_forecast_horizon_hours,
        )
        bundle = IntelligenceProviderBundle(
            country_code=country,
            radiation_provider=radiation,
            weather_provider=weather,
            radiation_name=radiation_name,
            weather_name=weather_name,
            engine=engine,
        )
        self._bundles[country] = bundle
        return bundle

    @property
    def dmi_client(self) -> DmiHarmonieClient:
        return self._dmi_client
