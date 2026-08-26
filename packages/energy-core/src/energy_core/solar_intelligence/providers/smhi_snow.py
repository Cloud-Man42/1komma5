"""SMHI SNOW weather forecast provider."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from energy_core.solar_intelligence.types import WeatherSnapshot

logger = logging.getLogger(__name__)

SNOW_BASE_URL = "https://opendata-download-metanalys.smhi.se/api/category/snow1g/version/1/geotype/point"


class SmhiSnowWeatherProvider:
    provider_name = "smhi-snow"

    # SNOW parameter ids (subset used by EMIC)
    PARAM_TEMP = 1
    PARAM_CLOUD = 16
    PARAM_PRECIP = 7
    PARAM_HUMIDITY = 6
    PARAM_WIND = 4

    def __init__(
        self,
        *,
        base_url: str = SNOW_BASE_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    def _point_url(self, *, latitude: float, longitude: float) -> str:
        return f"{self._base_url}/lon/{longitude:.6f}/lat/{latitude:.6f}/data.json"

    async def fetch_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[WeatherSnapshot]:
        del from_ts, to_ts
        url = self._point_url(latitude=latitude, longitude=longitude)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            payload = await self._get_json(client, url)
        if payload is None:
            return []
        return _merge_snow_parameters(payload, provider=self.provider_name)

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
        delay = 1.0
        for attempt in range(self._max_retries):
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    import asyncio

                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, dict) else None
            except httpx.HTTPError as exc:
                logger.warning("SMHI SNOW fetch failed attempt=%d: %s", attempt + 1, exc)
                if attempt + 1 >= self._max_retries:
                    return None
                import asyncio

                await asyncio.sleep(delay)
                delay *= 2
        return None


def _merge_snow_parameters(payload: dict[str, Any], *, provider: str) -> list[WeatherSnapshot]:
    """Parse SNOW multi-parameter response into hourly snapshots."""
    time_series = payload.get("timeSeries") or payload.get("timeseries") or []
    if not isinstance(time_series, list):
        return []

    by_ts: dict[datetime, dict[str, float | None]] = {}
    for entry in time_series:
        if not isinstance(entry, dict):
            continue
        raw_ts = entry.get("validTime") or entry.get("date")
        if raw_ts is None:
            continue
        ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        else:
            ts = ts.astimezone(UTC)

        params = entry.get("parameters") or entry.get("values") or []
        bucket = by_ts.setdefault(ts, {})
        if isinstance(params, list):
            for p in params:
                if not isinstance(p, dict):
                    continue
                name = str(p.get("name") or p.get("parameter") or "").lower()
                val = p.get("values", [None])[0] if "values" in p else p.get("value")
                try:
                    num = float(val) if val is not None else None
                except (TypeError, ValueError):
                    num = None
                if "t" in name or "temp" in name:
                    bucket["temperature_c"] = num
                elif "cloud" in name or "tcc" in name:
                    bucket["cloud_cover_pct"] = num * 100 if num is not None and num <= 1 else num
                elif "prec" in name or "rain" in name:
                    bucket["precipitation_mm"] = num
                elif "hum" in name or "rh" in name:
                    bucket["humidity_pct"] = num
                elif "wind" in name or "ws" in name:
                    bucket["wind_speed_ms"] = num

    snapshots: list[WeatherSnapshot] = []
    for ts, fields in sorted(by_ts.items()):
        snapshots.append(
            WeatherSnapshot(
                ts_utc=ts,
                temperature_c=fields.get("temperature_c"),
                cloud_cover_pct=fields.get("cloud_cover_pct"),
                precipitation_mm=fields.get("precipitation_mm"),
                humidity_pct=fields.get("humidity_pct"),
                wind_speed_ms=fields.get("wind_speed_ms"),
                provider=provider,
            )
        )
    return snapshots
