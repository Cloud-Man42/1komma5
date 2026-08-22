"""Open-Meteo weather forecast provider."""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime

import httpx

from energy_core.solar_forecast.azimuth import emic_azimuth_to_open_meteo
from energy_core.solar_forecast.constants import DEFAULT_AZIMUTH_DEG, DEFAULT_TILT_DEG
from energy_core.solar_forecast.types import (
    SolarSiteConfiguration,
    WeatherForecast,
    WeatherForecastPoint,
)
from energy_core.solar_forecast.weather import WeatherForecastProvider

logger = logging.getLogger(__name__)

MINUTELY_15_VARS = (
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "global_tilted_irradiance",
    "temperature_2m",
    "cloud_cover",
    "precipitation",
    "weather_code",
    "sunshine_duration",
)


class OpenMeteoWeatherProvider(WeatherForecastProvider):
    """Fetches 15-minutely solar radiation from Open-Meteo forecast API."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.open-meteo.com/v1/forecast",
        historical_url: str = "https://archive-api.open-meteo.com/v1/archive",
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._historical_url = historical_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def get_forecast(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
    ) -> WeatherForecast:
        params = self._build_params(site, from_ts, to_ts, historical=False)
        data = await self._fetch(self._base_url, params)
        return self._parse_response(site, data, provider="open-meteo")

    async def get_historical(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
    ) -> WeatherForecast:
        """Fetch historical weather for backfill (reanalysis, not forecast)."""
        params = self._build_params(site, from_ts, to_ts, historical=True)
        data = await self._fetch(self._historical_url, params)
        return self._parse_response(site, data, provider="open-meteo-historical")

    def _build_params(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
        *,
        historical: bool,
    ) -> dict[str, str | float]:
        tilt = site.tilt_deg if site.tilt_deg is not None else DEFAULT_TILT_DEG
        azimuth = site.azimuth_deg if site.azimuth_deg is not None else DEFAULT_AZIMUTH_DEG
        om_azimuth = emic_azimuth_to_open_meteo(azimuth)

        start = from_ts.astimezone(UTC).strftime("%Y-%m-%d")
        end = to_ts.astimezone(UTC).strftime("%Y-%m-%d")

        params: dict[str, str | float] = {
            "latitude": site.latitude,
            "longitude": site.longitude,
            "timezone": site.timezone,
            "tilt": tilt,
            "azimuth": om_azimuth,
        }

        if historical:
            params["start_date"] = start
            params["end_date"] = end
            params["hourly"] = ",".join(MINUTELY_15_VARS)
        else:
            # Compute forecast hours needed
            hours = max(1, int((to_ts - from_ts).total_seconds() / 3600) + 2)
            params["forecast_minutely_15"] = min(hours * 4, 192)  # up to 48h in 15-min steps
            params["minutely_15"] = ",".join(MINUTELY_15_VARS)

        if self._api_key:
            params["apikey"] = self._api_key

        return params

    async def _fetch(self, url: str, params: dict[str, str | float]) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            if response.status_code == 429:
                raise WeatherProviderRateLimitError("Open-Meteo rate limit exceeded")
            if response.status_code >= 500:
                raise WeatherProviderUnavailableError(f"Open-Meteo server error: {response.status_code}")
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise WeatherProviderError(data.get("reason", data["error"]))
            return data

    def _parse_response(
        self,
        site: SolarSiteConfiguration,
        data: dict,
        *,
        provider: str,
    ) -> WeatherForecast:
        block = data.get("minutely_15") or data.get("hourly")
        if not block:
            raise WeatherProviderError("Missing minutely_15/hourly block in response")

        times = block.get("time")
        if not times:
            raise WeatherProviderError("Missing time array in weather response")

        def _series(key: str) -> list[float | None]:
            raw = block.get(key)
            if raw is None:
                return [None] * len(times)
            if len(raw) != len(times):
                raise WeatherProviderError(f"Length mismatch for {key}")
            return raw

        ghi = _series("shortwave_radiation")
        direct = _series("direct_radiation")
        diffuse = _series("diffuse_radiation")
        gti = _series("global_tilted_irradiance")
        temp = _series("temperature_2m")
        cloud = _series("cloud_cover")
        precip = _series("precipitation")
        wcode = _series("weather_code")
        sunshine = _series("sunshine_duration")

        points: list[WeatherForecastPoint] = []
        for i, time_str in enumerate(times):
            ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            points.append(
                WeatherForecastPoint(
                    timestamp=ts,
                    ghi_wm2=_safe_float(ghi[i]),
                    direct_radiation_wm2=_safe_float(direct[i]),
                    diffuse_radiation_wm2=_safe_float(diffuse[i]),
                    gti_wm2=_safe_float(gti[i]),
                    cloud_cover_pct=_safe_float(cloud[i]),
                    temperature_c=_safe_float(temp[i]),
                    precipitation_mm=_safe_float(precip[i]),
                    weather_code=_safe_int(wcode[i]),
                    sunshine_duration_s=_safe_float(sunshine[i]),
                )
            )

        return WeatherForecast(
            site_id=site.site_id,
            fetched_at=datetime.now(UTC),
            provider=provider,
            points=tuple(points),
            source="live",
        )


def _safe_float(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_int(value: float | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class WeatherProviderError(Exception):
    pass


class WeatherProviderRateLimitError(WeatherProviderError):
    pass


class WeatherProviderUnavailableError(WeatherProviderError):
    pass
