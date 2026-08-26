"""Idempotent solar training sample backfill."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.daily_evaluation import actual_kwh_for_day, local_day_bounds
from energy_core.solar_forecast.historical import aggregate_buckets_from_readings, actual_energy_kwh
from energy_core.solar_intelligence.geometry import SolarGeometryService
from energy_core.solar_intelligence.normalizer import SolarWeatherNormalizer
from energy_core.solar_intelligence.physical_model import PhysicalPvModel, PvArraySpec
from energy_core.solar_intelligence.types import SampleQuality, TrainingSample
from energy_core.solar_forecast.types import SolarSiteConfiguration

logger = logging.getLogger(__name__)


class SolarBackfillService:
    """Build training samples from PV readings + radiation/weather providers."""

    def __init__(
        self,
        *,
        radiation_provider,
        weather_provider,
        open_meteo_fallback=None,
    ) -> None:
        self._radiation = radiation_provider
        self._weather = weather_provider
        self._fallback = open_meteo_fallback
        self._normalizer = SolarWeatherNormalizer()

    async def backfill_site(
        self,
        site: SolarSiteConfiguration,
        readings: list[tuple[datetime, float, float]],
        *,
        from_day: date,
        to_day: date,
        arrays: list[PvArraySpec] | None = None,
    ) -> list[TrainingSample]:
        if not site.enabled or site.latitude == 0 or site.longitude == 0:
            return []

        geometry = SolarGeometryService(
            latitude=site.latitude,
            longitude=site.longitude,
            timezone=site.timezone,
        )
        pv_arrays = arrays or [
            PvArraySpec(
                name="Main",
                capacity_kwp=site.installed_peak_power_kw,
                tilt_deg=site.tilt_deg or 35.0,
                azimuth_deg=site.azimuth_deg or 180.0,
            )
        ]
        model = PhysicalPvModel(
            arrays=pv_arrays,
            system_loss_percent=site.system_loss_percent,
            inverter_max_kw=site.inverter_max_power_kw,
            geometry=geometry,
        )

        day_start, _ = local_day_bounds(from_day, site.timezone)
        _, day_end = local_day_bounds(to_day, site.timezone)

        radiation = await self._fetch_radiation(site, day_start, day_end)
        weather = await self._fetch_weather(site, day_start, day_end)
        hourly = self._normalizer.merge_hourly(radiation, weather)

        hourly_by_ts = {h["ts_utc"]: h for h in hourly}
        samples: list[TrainingSample] = []

        day = from_day
        while day <= to_day:
            actual_day, completeness = actual_kwh_for_day(readings, day, site.timezone)
            quality = _quality_from_completeness(completeness)
            start, end = local_day_bounds(day, site.timezone)
            cur = start
            while cur < end:
                hour_key = cur.replace(minute=0, second=0, microsecond=0)
                wx = hourly_by_ts.get(hour_key, {})
                ghi = wx.get("ghi_wm2") or 0.0
                elev, _ = geometry.elevation_azimuth(cur)
                if elev <= 0:
                    cur += timedelta(hours=1)
                    continue

                power, poa = model.expected_power_w(
                    cur,
                    ghi_wm2=float(ghi),
                    dni_wm2=wx.get("dni_wm2"),
                    dhi_wm2=wx.get("dhi_wm2"),
                    temperature_c=wx.get("temperature_c"),
                )
                physical_kwh = model.energy_kwh(power)
                actual_hour = _actual_kwh_for_hour(readings, cur, end, site.timezone)

                samples.append(
                    TrainingSample(
                        site_id=site.site_id,
                        sample_date=day,
                        hour_utc=cur.astimezone(UTC).hour,
                        actual_kwh=actual_hour,
                        physical_kwh=round(physical_kwh, 4),
                        ghi_wm2=wx.get("ghi_wm2"),
                        dni_wm2=wx.get("dni_wm2"),
                        dhi_wm2=wx.get("dhi_wm2"),
                        poa_wm2=round(poa, 2) if poa else None,
                        solar_elevation_deg=round(elev, 2),
                        cloud_cover_pct=wx.get("cloud_cover_pct"),
                        temperature_c=wx.get("temperature_c"),
                        quality=quality if actual_hour is not None else SampleQuality.PARTIAL,
                        provenance="backfill",
                    )
                )
                cur += timedelta(hours=1)

            if actual_day > 0 and not samples:
                logger.debug("Backfill day %s site=%s actual=%.2f completeness=%.1f", day, site.site_id, actual_day, completeness)
            day += timedelta(days=1)

        return samples

    async def _fetch_radiation(self, site, from_ts, to_ts):
        try:
            data = await self._radiation.fetch_radiation(
                latitude=site.latitude,
                longitude=site.longitude,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            if data:
                return data
        except Exception:
            logger.exception("Radiation provider failed site=%s", site.site_id)
        if self._fallback:
            return await self._fallback.fetch_radiation(
                latitude=site.latitude,
                longitude=site.longitude,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        return []

    async def _fetch_weather(self, site, from_ts, to_ts):
        try:
            data = await self._weather.fetch_weather(
                latitude=site.latitude,
                longitude=site.longitude,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            if data:
                return data
        except Exception:
            logger.exception("Weather provider failed site=%s", site.site_id)
        if self._fallback:
            return await self._fallback.fetch_weather(
                latitude=site.latitude,
                longitude=site.longitude,
                from_ts=from_ts,
                to_ts=to_ts,
            )
        return []


def _quality_from_completeness(completeness_pct: float) -> SampleQuality:
    if completeness_pct >= 95.0:
        return SampleQuality.GOOD
    if completeness_pct >= 80.0:
        return SampleQuality.PARTIAL
    if completeness_pct >= 50.0:
        return SampleQuality.ESTIMATED
    return SampleQuality.REJECTED


def _actual_kwh_for_hour(
    readings: list[tuple[datetime, float, float]],
    hour_start: datetime,
    day_end: datetime,
    timezone: str,
) -> float | None:
    hour_end = min(hour_start + timedelta(hours=1), day_end)
    tz = ZoneInfo(timezone)
    hour_readings = [
        (ts, solar_w, _)
        for ts, solar_w, _ in readings
        if hour_start <= (ts if ts.tzinfo else ts.replace(tzinfo=UTC)) < hour_end
    ]
    if not hour_readings:
        return None
    buckets = aggregate_buckets_from_readings(hour_readings)
    return round(sum(actual_energy_kwh(b.avg_solar_w) for b in buckets), 4)
