"""Open-Meteo adapter as fallback weather/radiation provider."""

from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.open_meteo import OpenMeteoWeatherProvider
from energy_core.solar_forecast.types import SolarSiteConfiguration
from energy_core.solar_intelligence.types import RadiationSample, WeatherSnapshot


class OpenMeteoAdapter:
    """Wraps existing OpenMeteoWeatherProvider for solar intelligence interfaces."""

    provider_name = "open-meteo"

    def __init__(self, provider: OpenMeteoWeatherProvider) -> None:
        self._provider = provider

    @property
    def provider(self) -> OpenMeteoWeatherProvider:
        return self._provider

    async def fetch_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
        timezone: str = "UTC",
    ) -> list[WeatherSnapshot]:
        forecast = await self._get_weather(
            latitude=latitude,
            longitude=longitude,
            from_ts=from_ts,
            to_ts=to_ts,
            timezone=timezone,
        )
        snapshots: list[WeatherSnapshot] = []
        for p in forecast.points:
            ts = p.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            snapshots.append(
                WeatherSnapshot(
                    ts_utc=ts.astimezone(UTC),
                    temperature_c=p.temperature_c,
                    cloud_cover_pct=p.cloud_cover_pct,
                    precipitation_mm=p.precipitation_mm,
                    provider=self.provider_name,
                )
            )
        return snapshots

    async def fetch_radiation(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
        timezone: str = "UTC",
    ) -> list[RadiationSample]:
        forecast = await self._get_weather(
            latitude=latitude,
            longitude=longitude,
            from_ts=from_ts,
            to_ts=to_ts,
            timezone=timezone,
        )
        samples: list[RadiationSample] = []
        for p in forecast.points:
            ts = p.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            ts = ts.astimezone(UTC)
            if p.ghi_wm2 is not None:
                samples.append(
                    RadiationSample(ts_utc=ts, parameter="ghi", value_wm2=p.ghi_wm2, provider=self.provider_name)
                )
            if p.diffuse_radiation_wm2 is not None:
                samples.append(
                    RadiationSample(
                        ts_utc=ts,
                        parameter="dhi",
                        value_wm2=p.diffuse_radiation_wm2,
                        provider=self.provider_name,
                    )
                )
            if p.direct_radiation_wm2 is not None:
                samples.append(
                    RadiationSample(
                        ts_utc=ts,
                        parameter="dni",
                        value_wm2=p.direct_radiation_wm2,
                        provider=self.provider_name,
                    )
                )
        return samples

    async def _get_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
        timezone: str,
    ):
        site = SolarSiteConfiguration(
            site_id=0,
            latitude=latitude,
            longitude=longitude,
            installed_peak_power_kw=1.0,
            timezone=timezone,
            enabled=True,
        )
        now = datetime.now(UTC)
        tz = ZoneInfo(timezone)
        local_today = now.astimezone(tz).date()
        local_day_start = datetime.combine(local_today, time.min, tzinfo=tz).astimezone(UTC)
        if from_ts >= local_day_start:
            return await self._provider.get_forecast(site, from_ts, to_ts)
        if to_ts <= local_day_start:
            return await self._provider.get_historical(site, from_ts, to_ts)
        return await self._provider.get_forecast(site, local_day_start, to_ts)
