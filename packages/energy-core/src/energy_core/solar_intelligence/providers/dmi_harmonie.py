"""DMI HARMONIE forecast provider (Denmark weather + solar radiation)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from energy_core.solar_intelligence.types import RadiationSample, SampleQuality, WeatherSnapshot

logger = logging.getLogger(__name__)

DMI_EDR_BASE_URL = "https://opendataapi.dmi.dk/v1/forecastedr"
DMI_HARMONIE_COLLECTION = "harmonie_dini_sf"

DMI_RADIATION_PARAMS = (
    "global-radiation-flux",
    "downward-short-wave-radiation-flux-instant",
)
DMI_WEATHER_PARAMS = (
    "temperature-2m",
    "relative-humidity-2m",
    "low-cloud-cover",
    "medium-cloud-cover",
    "high-cloud-cover",
    "fraction-of-cloud-cover",
    "wind-speed-10m",
    "total-precipitation",
)
DMI_ALL_PARAMS = tuple(dict.fromkeys(DMI_RADIATION_PARAMS + DMI_WEATHER_PARAMS))


def _parse_ts(raw: str) -> datetime:
    ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num:  # NaN
        return None
    return num


def _kelvin_to_celsius(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 150.0:
        return round(value - 273.15, 2)
    return value


def _cloud_cover_pct(props: dict[str, Any]) -> float | None:
    fraction = _as_float(props.get("fraction-of-cloud-cover"))
    if fraction is not None:
        return round(min(100.0, max(0.0, fraction * 100.0 if fraction <= 1.0 else fraction)), 1)
    parts = [
        _as_float(props.get("low-cloud-cover")),
        _as_float(props.get("medium-cloud-cover")),
        _as_float(props.get("high-cloud-cover")),
    ]
    values = [v for v in parts if v is not None]
    if not values:
        return None
    return round(min(100.0, max(0.0, sum(values) / len(values))), 1)


def _ghi_wm2(props: dict[str, Any]) -> float | None:
    instant = _as_float(props.get("downward-short-wave-radiation-flux-instant"))
    if instant is not None and instant >= 0:
        return instant
    global_flux = _as_float(props.get("global-radiation-flux"))
    if global_flux is not None and global_flux >= 0:
        return global_flux
    return None


def _estimate_dhi_wm2(*, ghi: float, cloud_cover_pct: float | None) -> float:
    if cloud_cover_pct is None:
        return round(ghi * 0.3, 2)
    cloud_frac = min(1.0, max(0.0, cloud_cover_pct / 100.0))
    ratio = 0.15 + cloud_frac * 0.7
    return round(ghi * ratio, 2)


def parse_dmi_geojson(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse DMI EDR GeoJSON into normalized hourly rows."""
    features = payload.get("features") or []
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties")
        if not isinstance(props, dict):
            continue
        step = props.get("step")
        if step is None:
            continue
        ts = _parse_ts(str(step))
        cloud = _cloud_cover_pct(props)
        ghi = _ghi_wm2(props)
        precip_total = _as_float(props.get("total-precipitation"))
        rows.append(
            {
                "ts_utc": ts,
                "ghi_wm2": ghi,
                "dhi_wm2": _estimate_dhi_wm2(ghi=ghi, cloud_cover_pct=cloud) if ghi is not None else None,
                "temperature_c": _kelvin_to_celsius(_as_float(props.get("temperature-2m"))),
                "cloud_cover_pct": cloud,
                "humidity_pct": _as_float(props.get("relative-humidity-2m")),
                "wind_speed_ms": _as_float(props.get("wind-speed-10m")),
                "precipitation_total_mm": precip_total,
            }
        )
    rows.sort(key=lambda row: row["ts_utc"])
    for index, row in enumerate(rows):
        prev_total = rows[index - 1]["precipitation_total_mm"] if index > 0 else None
        current_total = row["precipitation_total_mm"]
        if prev_total is not None and current_total is not None:
            row["precipitation_mm"] = max(0.0, round(current_total - prev_total, 3))
        else:
            row["precipitation_mm"] = None
    return rows


def _filter_rows(rows: list[dict[str, Any]], *, from_ts: datetime, to_ts: datetime) -> list[dict[str, Any]]:
    return [row for row in rows if from_ts <= row["ts_utc"] <= to_ts]


class DmiHarmonieClient:
    """Shared HTTP client for DMI HARMONIE point forecasts."""

    provider_name = "dmi-harmonie"

    def __init__(
        self,
        *,
        base_url: str = DMI_EDR_BASE_URL,
        collection: str = DMI_HARMONIE_COLLECTION,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._collection = collection
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._cache: dict[str, list[dict[str, Any]]] = {}

    def _cache_key(self, *, latitude: float, longitude: float, from_ts: datetime, to_ts: datetime) -> str:
        return f"{latitude:.5f}:{longitude:.5f}:{from_ts.isoformat()}:{to_ts.isoformat()}"

    def _position_url(self, *, latitude: float, longitude: float) -> str:
        coords = quote(f"POINT({longitude:.6f} {latitude:.6f})")
        params = ",".join(DMI_ALL_PARAMS)
        return (
            f"{self._base_url}/collections/{self._collection}/position"
            f"?coords={coords}&crs=crs84&parameter-name={params}&f=GeoJSON"
        )

    async def fetch_rows(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[dict[str, Any]]:
        key = self._cache_key(latitude=latitude, longitude=longitude, from_ts=from_ts, to_ts=to_ts)
        if key in self._cache:
            return list(self._cache[key])

        url = self._position_url(latitude=latitude, longitude=longitude)
        payload = await self._get_json(url)
        if payload is None:
            self._cache[key] = []
            return []

        rows = _filter_rows(parse_dmi_geojson(payload), from_ts=from_ts, to_ts=to_ts)
        self._cache[key] = rows
        return list(rows)

    async def _get_json(self, url: str) -> dict[str, Any] | None:
        delay = 1.0
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    resp = await client.get(url, headers={"Accept": "application/json"})
                    if resp.status_code == 429:
                        logger.warning("DMI HARMONIE rate limited, retry %d", attempt + 1)
                        import asyncio

                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data if isinstance(data, dict) else None
                except httpx.HTTPError as exc:
                    logger.warning("DMI HARMONIE fetch failed attempt=%d: %s", attempt + 1, exc)
                    if attempt + 1 >= self._max_retries:
                        return None
                    import asyncio

                    await asyncio.sleep(delay)
                    delay *= 2
        return None


class DmiHarmonieRadiationProvider:
    provider_name = DmiHarmonieClient.provider_name

    def __init__(self, client: DmiHarmonieClient) -> None:
        self._client = client

    async def fetch_radiation(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[RadiationSample]:
        rows = await self._client.fetch_rows(
            latitude=latitude,
            longitude=longitude,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        samples: list[RadiationSample] = []
        for row in rows:
            ts = row["ts_utc"]
            ghi = row.get("ghi_wm2")
            dhi = row.get("dhi_wm2")
            if ghi is not None:
                samples.append(
                    RadiationSample(
                        ts_utc=ts,
                        parameter="ghi",
                        value_wm2=ghi,
                        quality=SampleQuality.GOOD,
                        provider=self.provider_name,
                    )
                )
            if dhi is not None:
                samples.append(
                    RadiationSample(
                        ts_utc=ts,
                        parameter="dhi",
                        value_wm2=dhi,
                        quality=SampleQuality.ESTIMATED,
                        provider=self.provider_name,
                    )
                )
        return samples


class DmiHarmonieWeatherProvider:
    provider_name = DmiHarmonieClient.provider_name

    def __init__(self, client: DmiHarmonieClient) -> None:
        self._client = client

    async def fetch_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[WeatherSnapshot]:
        rows = await self._client.fetch_rows(
            latitude=latitude,
            longitude=longitude,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        return [
            WeatherSnapshot(
                ts_utc=row["ts_utc"],
                temperature_c=row.get("temperature_c"),
                cloud_cover_pct=row.get("cloud_cover_pct"),
                precipitation_mm=row.get("precipitation_mm"),
                humidity_pct=row.get("humidity_pct"),
                wind_speed_ms=row.get("wind_speed_ms"),
                provider=self.provider_name,
            )
            for row in rows
        ]
