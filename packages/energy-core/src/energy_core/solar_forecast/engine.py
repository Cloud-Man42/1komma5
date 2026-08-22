"""Solar forecast engine — orchestrates physical model, correction, confidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_forecast.confidence import SolarForecastConfidenceService, cloud_variability
from energy_core.solar_forecast.correction import SolarForecastCorrectionEngine
from energy_core.solar_forecast.physical import baseline_energy_kwh, baseline_power_w
from energy_core.solar_forecast.types import (
    MODEL_VERSION,
    ModelState,
    SitePerformanceProfile,
    SolarForecast,
    SolarForecastModelProfile,
    SolarForecastPoint,
    SolarSiteConfiguration,
    WeatherForecast,
    WeatherSource,
)


class SolarForecastEngine:
    def __init__(
        self,
        *,
        correction: SolarForecastCorrectionEngine | None = None,
        confidence_svc: SolarForecastConfidenceService | None = None,
        horizon_hours: int = 48,
    ) -> None:
        self._correction = correction or SolarForecastCorrectionEngine()
        self._confidence = confidence_svc or SolarForecastConfidenceService()
        self._horizon_hours = horizon_hours

    def generate(
        self,
        site: SolarSiteConfiguration,
        weather: WeatherForecast,
        profile: SitePerformanceProfile,
        *,
        now: datetime | None = None,
        weather_source: WeatherSource = "live",
        cache_age_minutes: float = 0.0,
        model_profile: SolarForecastModelProfile | None = None,
    ) -> SolarForecast:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        v2_profile = model_profile or SolarForecastModelProfile(site_id=site.site_id)
        v2_factor = v2_profile.correction_factor

        tz = ZoneInfo(site.timezone)
        local_now = now.astimezone(tz)
        local_today = local_now.date()
        local_tomorrow = local_today + timedelta(days=1)

        end = now + timedelta(hours=self._horizon_hours)
        relevant = [p for p in weather.points if now <= p.timestamp < end]
        if not relevant:
            relevant = list(weather.points)

        max_power_w = site.inverter_max_power_kw * 1000.0 if site.inverter_max_power_kw else None
        if max_power_w is None:
            max_power_w = site.installed_peak_power_kw * 1000.0

        cloud_vals = [p.cloud_cover_pct for p in relevant]
        cloud_var = cloud_variability(cloud_vals)

        forecast_points: list[SolarForecastPoint] = []
        point_confidences: list[float] = []

        for wp in relevant:
            baseline_w = baseline_power_w(wp, site)
            corrected_w, factor = self._correction.apply(baseline_w, profile, wp, wp.timestamp)
            corrected_w *= v2_factor
            factor *= v2_factor
            if site.inverter_max_power_kw:
                corrected_w = min(corrected_w, site.inverter_max_power_kw * 1000.0)

            hours_ahead = (wp.timestamp - now).total_seconds() / 3600.0
            conf = self._confidence.compute_point_confidence(
                hours_ahead=hours_ahead,
                weather_source=weather_source,
                profile=profile,
                cloud_var=cloud_var,
                cache_age_minutes=cache_age_minutes,
            )
            lower, upper = self._confidence.interval_bounds(
                corrected_w, conf, profile, max_power_w=max_power_w
            )
            energy = baseline_energy_kwh(corrected_w)
            forecast_points.append(
                SolarForecastPoint(
                    timestamp=wp.timestamp,
                    baseline_power_w=baseline_w,
                    corrected_power_w=corrected_w,
                    expected_energy_kwh=energy,
                    lower_bound_power_w=lower,
                    upper_bound_power_w=upper,
                    confidence=conf,
                    gti_wm2=wp.gti_wm2 or wp.ghi_wm2,
                    cloud_cover_pct=wp.cloud_cover_pct,
                    correction_factor=factor,
                )
            )
            point_confidences.append(conf)

        agg_conf = self._confidence.aggregate_confidence(point_confidences)
        quality = self._confidence.quality_from_confidence(agg_conf)

        today_pts = [p for p in forecast_points if p.timestamp.astimezone(tz).date() == local_today]
        tomorrow_pts = [p for p in forecast_points if p.timestamp.astimezone(tz).date() == local_tomorrow]
        future_today = [p for p in today_pts if p.timestamp >= now]

        raw_today = sum(baseline_energy_kwh(p.baseline_power_w) for p in today_pts)
        raw_tomorrow = sum(baseline_energy_kwh(p.baseline_power_w) for p in tomorrow_pts) if tomorrow_pts else None

        expected_today = sum(p.expected_energy_kwh for p in today_pts)
        remaining_today = sum(p.expected_energy_kwh for p in future_today)
        expected_tomorrow = sum(p.expected_energy_kwh for p in tomorrow_pts) if tomorrow_pts else None

        lower_today = sum(baseline_energy_kwh(p.lower_bound_power_w) for p in today_pts)
        upper_today = sum(baseline_energy_kwh(p.upper_bound_power_w) for p in today_pts)

        peak_w = 0.0
        peak_time: datetime | None = None
        for p in future_today:
            if p.corrected_power_w > peak_w:
                peak_w = p.corrected_power_w
                peak_time = p.timestamp

        summary = self._confidence.weather_summary(weather, now=now)

        return SolarForecast(
            site_id=site.site_id,
            generated_at=now,
            model_version=MODEL_VERSION,
            quality=quality,
            weather_source=weather_source,
            expected_today_kwh=expected_today,
            remaining_today_kwh=remaining_today,
            expected_tomorrow_kwh=expected_tomorrow,
            peak_power_w=peak_w,
            peak_time=peak_time,
            confidence=agg_conf,
            lower_today_kwh=lower_today,
            upper_today_kwh=upper_today,
            weather_summary=summary,
            points=tuple(forecast_points),
            raw_forecast_today_kwh=raw_today,
            raw_forecast_tomorrow_kwh=raw_tomorrow,
            corrected_forecast_today_kwh=expected_today,
            corrected_forecast_tomorrow_kwh=expected_tomorrow,
            correction_factor=v2_factor,
            model_state=v2_profile.model_state,
            confidence_score=v2_profile.confidence_score,
            historical_samples=v2_profile.historical_samples,
        )
