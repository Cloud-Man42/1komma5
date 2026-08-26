"""SMHI STRÅNG radiation parameter catalog and provider."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from energy_core.solar_intelligence.types import RadiationSample, SampleQuality

logger = logging.getLogger(__name__)

STRANG_MISSING_VALUE = -999.0
STRANG_BASE_URL = (
    "https://opendata-download-metanalys.smhi.se/api/category/strang1g/version/1/geotype/point"
)


class StrangParameterCatalog:
    """Verified STRÅNG parameter ids — keep mapping isolated from business logic."""

    GLOBAL_IRRADIANCE = 117
    DIFFUSE_IRRADIANCE = 122
    DIRECT_NORMAL = 108

    _NAMES: dict[int, str] = {
        117: "ghi",
        122: "dhi",
        108: "dni",
    }

    @classmethod
    def name_for(cls, parameter_id: int) -> str:
        return cls._NAMES.get(parameter_id, f"param_{parameter_id}")

    @classmethod
    def default_parameters(cls) -> tuple[int, ...]:
        return (cls.GLOBAL_IRRADIANCE, cls.DIFFUSE_IRRADIANCE)


def _parse_strang_timeseries(payload: dict[str, Any], *, parameter_id: int, provider: str) -> list[RadiationSample]:
    param_name = StrangParameterCatalog.name_for(parameter_id)
    series = payload.get("values") or payload.get("timeSeries") or []
    if isinstance(series, dict):
        series = series.get("values") or series.get("points") or []

    samples: list[RadiationSample] = []
    for entry in series:
        if not isinstance(entry, dict):
            continue
        raw_ts = entry.get("date") or entry.get("time") or entry.get("validTime")
        raw_val = entry.get("value")
        if raw_val is None and "values" in entry:
            vals = entry["values"]
            raw_val = vals[0] if vals else None
        if raw_ts is None:
            continue
        ts = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        else:
            ts = ts.astimezone(UTC)

        quality = SampleQuality.GOOD
        value: float | None
        try:
            num = float(raw_val) if raw_val is not None else STRANG_MISSING_VALUE
        except (TypeError, ValueError):
            quality = SampleQuality.MISSING
            value = None
        else:
            if num <= STRANG_MISSING_VALUE + 1:
                quality = SampleQuality.MISSING
                value = None
            else:
                value = num

        samples.append(
            RadiationSample(
                ts_utc=ts,
                parameter=param_name,
                value_wm2=value,
                quality=quality,
                provider=provider,
            )
        )
    return samples


class SmhiStrangRadiationProvider:
    provider_name = "smhi-strang"

    def __init__(
        self,
        *,
        base_url: str = STRANG_BASE_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    def _point_url(self, *, latitude: float, longitude: float, parameter_id: int) -> str:
        return (
            f"{self._base_url}/lon/{longitude:.6f}/lat/{latitude:.6f}/"
            f"parameter/{parameter_id}/data.json"
        )

    async def fetch_radiation(
        self,
        *,
        latitude: float,
        longitude: float,
        from_ts: datetime,
        to_ts: datetime,
    ) -> list[RadiationSample]:
        del from_ts, to_ts  # STRÅNG point API returns full series; filter client-side
        all_samples: list[RadiationSample] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for param_id in StrangParameterCatalog.default_parameters():
                url = self._point_url(latitude=latitude, longitude=longitude, parameter_id=param_id)
                payload = await self._get_json(client, url)
                if payload is None:
                    continue
                all_samples.extend(_parse_strang_timeseries(payload, parameter_id=param_id, provider=self.provider_name))
        return sorted(all_samples, key=lambda s: (s.ts_utc, s.parameter))

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any] | None:
        delay = 1.0
        for attempt in range(self._max_retries):
            try:
                resp = await client.get(url)
                if resp.status_code == 429:
                    logger.warning("SMHI STRÅNG rate limited, retry %d", attempt + 1)
                    import asyncio

                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, dict) else None
            except httpx.HTTPError as exc:
                logger.warning("SMHI STRÅNG fetch failed url=%s attempt=%d: %s", url, attempt + 1, exc)
                if attempt + 1 >= self._max_retries:
                    return None
                import asyncio

                await asyncio.sleep(delay)
                delay *= 2
        return None
