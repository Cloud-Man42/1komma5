"""Provider protocols for solar intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from energy_core.solar_intelligence.types import RadiationSample, WeatherSnapshot


class ISolarRadiationProvider(Protocol):
    provider_name: str

    async def fetch_radiation(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[RadiationSample]: ...


class IWeatherForecastProvider(Protocol):
    provider_name: str

    async def fetch_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[WeatherSnapshot]: ...
