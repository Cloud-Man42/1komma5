"""Normalize provider weather/radiation into unified hourly inputs."""

from __future__ import annotations

from datetime import datetime
from collections import defaultdict

from energy_core.solar_intelligence.types import RadiationSample, SampleQuality, WeatherSnapshot


class SolarWeatherNormalizer:
    """Merge radiation + weather streams keyed by UTC hour."""

    def merge_hourly(
        self,
        radiation: list[RadiationSample],
        weather: list[WeatherSnapshot],
    ) -> list[dict]:
        rad_by_hour: dict[datetime, dict[str, float | None]] = defaultdict(dict)
        for r in radiation:
            if r.quality == SampleQuality.MISSING or r.value_wm2 is None:
                continue
            hour = r.ts_utc.replace(minute=0, second=0, microsecond=0)
            rad_by_hour[hour][r.parameter] = r.value_wm2

        wx_by_hour: dict[datetime, WeatherSnapshot] = {}
        for w in weather:
            hour = w.ts_utc.replace(minute=0, second=0, microsecond=0)
            wx_by_hour[hour] = w

        hours = sorted(set(rad_by_hour.keys()) | set(wx_by_hour.keys()))
        merged: list[dict] = []
        for hour in hours:
            rad = rad_by_hour.get(hour, {})
            wx = wx_by_hour.get(hour)
            merged.append(
                {
                    "ts_utc": hour,
                    "ghi_wm2": rad.get("ghi"),
                    "dni_wm2": rad.get("dni"),
                    "dhi_wm2": rad.get("dhi"),
                    "temperature_c": wx.temperature_c if wx else None,
                    "cloud_cover_pct": wx.cloud_cover_pct if wx else None,
                    "precipitation_mm": wx.precipitation_mm if wx else None,
                }
            )
        return merged
