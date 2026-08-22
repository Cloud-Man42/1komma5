"""Weather forecast provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecast


class WeatherForecastProvider(ABC):
    @abstractmethod
    async def get_forecast(
        self,
        site: SolarSiteConfiguration,
        from_ts: datetime,
        to_ts: datetime,
    ) -> WeatherForecast:
        """Fetch weather forecast for a site between from_ts and to_ts."""
