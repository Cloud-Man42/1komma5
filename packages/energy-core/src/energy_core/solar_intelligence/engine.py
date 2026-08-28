"""Solar Intelligence forecast engine."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.constants import INTERVAL_HOURS
from energy_core.solar_forecast.types import confidence_label_from_score
from energy_core.solar_intelligence.calibration import SolarCalibrationService, build_feature_vector
from energy_core.solar_intelligence.confidence import confidence_score_from_metrics, radiation_confidence_for_location
from energy_core.solar_intelligence.geometry import SolarGeometryService
from energy_core.solar_intelligence.normalizer import SolarWeatherNormalizer
from energy_core.solar_intelligence.physical_model import PhysicalPvModel, PvArraySpec
from energy_core.solar_intelligence.types import (
    INTELLIGENCE_MODEL_VERSION,
    ForecastStatus,
    HourlyForecastPoint,
    IntelligenceForecast,
    SolarModelRecord,
)
from energy_core.solar_forecast.types import SolarSiteConfiguration

logger = logging.getLogger(__name__)


class SolarIntelligenceEngine:
    """Generate hourly + daily forecasts using SMHI physics + Ridge correction."""

    def __init__(
        self,
        *,
        radiation_provider,
        weather_provider,
        open_meteo_fallback=None,
        horizon_hours: int = 48,
    ) -> None:
        self._radiation = radiation_provider
        self._weather = weather_provider
        self._fallback = open_meteo_fallback
        self._horizon_hours = horizon_hours
        self._normalizer = SolarWeatherNormalizer()
        self._calibration = SolarCalibrationService()

    async def generate(
        self,
        site: SolarSiteConfiguration,
        *,
        arrays: list[PvArraySpec] | None = None,
        champion: SolarModelRecord | None = None,
        now: datetime | None = None,
        last_known_good: IntelligenceForecast | None = None,
    ) -> IntelligenceForecast:
        now = now or datetime.now(UTC)
        status = ForecastStatus.HEALTHY
        weather_source = getattr(self._radiation, "provider_name", "unknown")

        try:
            to_ts = now + timedelta(hours=self._horizon_hours)
            radiation = await self._fetch_radiation(site, now, to_ts)
            weather = await self._fetch_weather(site, now, to_ts)
            if not radiation:
                status = ForecastStatus.DEGRADED
                weather_source = "open-meteo"
        except Exception:
            logger.exception("Solar intelligence provider failure site=%s", site.site_id)
            if last_known_good is not None:
                return _degraded_from_last_good(last_known_good)
            return _unavailable_forecast(site.site_id, now)

        hourly_inputs = self._normalizer.merge_hourly(radiation, weather)
        if not hourly_inputs:
            if last_known_good is not None:
                return _degraded_from_last_good(last_known_good)
            status = ForecastStatus.DEGRADED
            weather_source = "open-meteo"

        geometry = SolarGeometryService(latitude=site.latitude, longitude=site.longitude, timezone=site.timezone)
        pv_arrays = arrays or [
            PvArraySpec(
                name="Main",
                capacity_kwp=site.installed_peak_power_kw,
                tilt_deg=site.tilt_deg or 35.0,
                azimuth_deg=site.azimuth_deg or 180.0,
            )
        ]
        physical = PhysicalPvModel(
            arrays=pv_arrays,
            system_loss_percent=site.system_loss_percent,
            inverter_max_kw=site.inverter_max_power_kw,
            geometry=geometry,
        )

        rad_conf = radiation_confidence_for_location(
            latitude=site.latitude,
            longitude=site.longitude,
            provider=getattr(self._radiation, "provider_name", "unknown"),
        )

        hourly_points: list[HourlyForecastPoint] = []
        for row in hourly_inputs:
            ts = row["ts_utc"]
            if ts < now - timedelta(minutes=30):
                continue
            ghi = float(row.get("ghi_wm2") or 0.0)
            power_w, poa = physical.expected_power_w(
                ts,
                ghi_wm2=ghi,
                dni_wm2=row.get("dni_wm2"),
                dhi_wm2=row.get("dhi_wm2"),
                temperature_c=row.get("temperature_c"),
            )
            learned_pct = _learned_correction(champion, ts, row, site, pv_arrays[0])
            corrected_w = power_w * (1.0 + learned_pct)
            spread = 0.12 if rad_conf.value == "HIGH" else 0.18
            hourly_points.append(
                HourlyForecastPoint(
                    timestamp=ts,
                    physical_w=round(power_w, 1),
                    corrected_w=round(corrected_w, 1),
                    lower_w=round(corrected_w * (1.0 - spread), 1),
                    upper_w=round(corrected_w * (1.0 + spread), 1),
                    confidence=80.0,
                    ghi_wm2=row.get("ghi_wm2"),
                    poa_wm2=poa,
                    breakdown={
                        "physical_w": power_w,
                        "learned_correction_pct": learned_pct * 100.0,
                        "cloud_adj": 0.0,
                    },
                )
            )

        local_today = now.astimezone(ZoneInfo(site.timezone)).date()
        today_kwh, tomorrow_kwh, day_after_kwh = _daily_totals(hourly_points, local_today, site.timezone)
        physical_today = sum(
            p.physical_w / 1000.0 * INTERVAL_HOURS
            for p in hourly_points
            if p.timestamp.astimezone(ZoneInfo(site.timezone)).date() == local_today
        )
        remaining = sum(
            p.corrected_w / 1000.0 * INTERVAL_HOURS
            for p in hourly_points
            if p.timestamp > now and p.timestamp.astimezone(ZoneInfo(site.timezone)).date() == local_today
        )
        peak_w = max((p.corrected_w for p in hourly_points), default=0.0)
        peak_time = next((p.timestamp for p in hourly_points if p.corrected_w == peak_w), None)

        wape = champion.wape if champion else None
        conf_score = confidence_score_from_metrics(wape=wape, sample_count=champion.sample_count if champion else 0, radiation=rad_conf)
        spread_day = 0.1 if conf_score >= 70 else 0.15

        from energy_core.solar_intelligence.charging_signals import build_charging_signals

        charging = build_charging_signals(
            hourly=hourly_points,
            expected_today_kwh=today_kwh,
            now=now,
            timezone=site.timezone,
            confidence=conf_score,
        )

        return IntelligenceForecast(
            site_id=site.site_id,
            generated_at=now,
            model_version=INTELLIGENCE_MODEL_VERSION,
            status=status,
            expected_today_kwh=round(today_kwh, 2),
            remaining_today_kwh=round(remaining, 2),
            expected_tomorrow_kwh=round(tomorrow_kwh, 2) if tomorrow_kwh else None,
            expected_day_after_kwh=round(day_after_kwh, 2) if day_after_kwh else None,
            peak_power_w=round(peak_w, 1),
            peak_time=peak_time,
            lower_today_kwh=round(today_kwh * (1.0 - spread_day), 2),
            upper_today_kwh=round(today_kwh * (1.0 + spread_day), 2),
            confidence=conf_score,
            confidence_label=confidence_label_from_score(conf_score),
            radiation_confidence=rad_conf,
            hourly=tuple(hourly_points),
            physical_today_kwh=round(physical_today, 2),
            learned_correction_pct=round(champion.bias_pct or 0.0, 2) if champion else 0.0,
            weather_source=weather_source,
            explainability={
                "clear_sky_kwh": round(physical_today, 2),
                "learned_correction_pct": champion.bias_pct or 0.0 if champion else 0.0,
            },
            charging_signals=charging,
        )

    async def _fetch_radiation(self, site, from_ts, to_ts):
        try:
            data = await self._radiation.fetch_radiation(
                latitude=site.latitude, longitude=site.longitude, from_ts=from_ts, to_ts=to_ts
            )
            if data:
                return data
        except Exception:
            logger.warning("STRÅNG failed, using fallback site=%s", site.site_id)
        if self._fallback:
            return await self._fallback.fetch_radiation(
                latitude=site.latitude, longitude=site.longitude, from_ts=from_ts, to_ts=to_ts, timezone=site.timezone
            )
        return []

    async def _fetch_weather(self, site, from_ts, to_ts):
        try:
            data = await self._weather.fetch_weather(
                latitude=site.latitude, longitude=site.longitude, from_ts=from_ts, to_ts=to_ts
            )
            if data:
                return data
        except Exception:
            logger.warning("SNOW failed, using fallback site=%s", site.site_id)
        if self._fallback:
            return await self._fallback.fetch_weather(
                latitude=site.latitude, longitude=site.longitude, from_ts=from_ts, to_ts=to_ts, timezone=site.timezone
            )
        return []


def _learned_correction(champion, ts, row, site, array) -> float:
    if champion is None or not champion.coefficients:
        return 0.0
    from energy_core.solar_intelligence.types import TrainingSample

    sample = TrainingSample(
        site_id=site.site_id,
        sample_date=ts.astimezone(ZoneInfo(site.timezone)).date(),
        hour_utc=ts.hour,
        actual_kwh=None,
        physical_kwh=None,
        ghi_wm2=row.get("ghi_wm2"),
        dni_wm2=row.get("dni_wm2"),
        dhi_wm2=row.get("dhi_wm2"),
        poa_wm2=row.get("poa_wm2"),
        solar_elevation_deg=None,
        cloud_cover_pct=row.get("cloud_cover_pct"),
        temperature_c=row.get("temperature_c"),
    )
    x = build_feature_vector(
        sample,
        installed_kwp=site.installed_peak_power_kw,
        tilt=array.tilt_deg,
        azimuth=array.azimuth_deg,
    )
    corr = champion.coefficients.get("intercept", 0.0)
    for i, name in enumerate(
        ("hour_sin", "hour_cos", "doy_sin", "doy_cos", "solar_elevation", "poa_irradiance", "ghi", "cloud_cover", "temperature", "installed_kwp", "panel_tilt", "panel_azimuth")
    ):
        corr += champion.coefficients.get(name, 0.0) * x[i]
    return max(-0.5, min(0.5, corr))


def _daily_totals(hourly: list[HourlyForecastPoint], today: date, timezone: str) -> tuple[float, float | None, float | None]:
    tz = ZoneInfo(timezone)
    by_day: dict[date, float] = {}
    for p in hourly:
        d = p.timestamp.astimezone(tz).date()
        by_day[d] = by_day.get(d, 0.0) + p.corrected_w / 1000.0 * INTERVAL_HOURS
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    return by_day.get(today, 0.0), by_day.get(tomorrow), by_day.get(day_after)


def _degraded_from_last_good(lkg: IntelligenceForecast) -> IntelligenceForecast:
    from dataclasses import replace

    return replace(lkg, status=ForecastStatus.DEGRADED)


def _unavailable_forecast(site_id: int, now: datetime) -> IntelligenceForecast:
    return IntelligenceForecast(
        site_id=site_id,
        generated_at=now,
        model_version=INTELLIGENCE_MODEL_VERSION,
        status=ForecastStatus.UNAVAILABLE,
        expected_today_kwh=0.0,
        remaining_today_kwh=0.0,
        expected_tomorrow_kwh=None,
        expected_day_after_kwh=None,
        peak_power_w=0.0,
        peak_time=None,
        lower_today_kwh=0.0,
        upper_today_kwh=0.0,
        confidence=0.0,
        confidence_label="Low",
        radiation_confidence=radiation_confidence_for_location(latitude=0, longitude=0, provider="unknown"),
        hourly=(),
        physical_today_kwh=0.0,
        learned_correction_pct=0.0,
        weather_source="none",
    )
