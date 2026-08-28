"""DMI HARMONIE adapter for the v2 solar forecast weather pipeline."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecast, WeatherForecastPoint
from energy_core.solar_forecast.weather import WeatherForecastProvider
from energy_core.solar_intelligence.providers.dmi_harmonie import DmiHarmonieClient


class DmiWeatherForecastProvider(WeatherForecastProvider):
    provider_name = DmiHarmonieClient.provider_name

    def __init__(self, client: DmiHarmonieClient) -> None:
        self._client = client

    async def get_forecast(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
    ) -> WeatherForecast:
        rows = await self._client.fetch_rows(
            latitude=site.latitude,
            longitude=site.longitude,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        points = tuple(
            WeatherForecastPoint(
                timestamp=row["ts_utc"],
                ghi_wm2=row.get("ghi_wm2"),
                diffuse_radiation_wm2=row.get("dhi_wm2"),
                cloud_cover_pct=row.get("cloud_cover_pct"),
                temperature_c=row.get("temperature_c"),
                precipitation_mm=row.get("precipitation_mm"),
                wind_speed_ms=row.get("wind_speed_ms"),
                relative_humidity_pct=row.get("humidity_pct"),
            )
            for row in rows
        )
        return WeatherForecast(
            site_id=site.site_id,
            fetched_at=datetime.now(UTC),
            provider=self.provider_name,
            points=points,
            source="live",
        )
