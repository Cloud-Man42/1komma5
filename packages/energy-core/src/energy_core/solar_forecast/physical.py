"""Physical PV baseline model."""

from __future__ import annotations

import math
from datetime import datetime

from energy_core.solar_forecast.constants import (
    DEFAULT_AZIMUTH_DEG,
    DEFAULT_TILT_DEG,
    INTERVAL_HOURS,
    REFERENCE_TEMP_C,
    TEMP_COEFFICIENT_PER_C,
)
from energy_core.solar_forecast.types import SolarSiteConfiguration, WeatherForecastPoint


def effective_tilt_azimuth(site: SolarSiteConfiguration) -> tuple[float, float, bool, bool]:
    tilt = site.tilt_deg if site.tilt_deg is not None else DEFAULT_TILT_DEG
    azimuth = site.azimuth_deg if site.azimuth_deg is not None else DEFAULT_AZIMUTH_DEG
    tilt_est = site.tilt_deg is None or site.tilt_estimated
    az_est = site.azimuth_deg is None or site.azimuth_estimated
    return tilt, azimuth, tilt_est, az_est


def irradiance_wm2(point: WeatherForecastPoint, site: SolarSiteConfiguration) -> float:
    """Return panel-plane irradiance W/m², preferring GTI then transposition fallback."""
    if point.gti_wm2 is not None and point.gti_wm2 >= 0:
        return point.gti_wm2

    ghi = point.ghi_wm2 or 0.0
    direct = point.direct_radiation_wm2 or 0.0
    diffuse = point.diffuse_radiation_wm2
    if diffuse is None and ghi > 0:
        diffuse = max(0.0, ghi - direct)

    if ghi <= 0 and direct <= 0:
        return 0.0

    tilt, _, _, _ = effective_tilt_azimuth(site)
    elevation, _ = _solar_geometry(point.timestamp, site.latitude, site.longitude, site.timezone)
    if elevation <= 0:
        return 0.0

    # Isotropic transposition approximation
    tilt_rad = math.radians(tilt)
    elev_rad = math.radians(elevation)
    cos_incidence = max(0.0, math.sin(elev_rad) * math.cos(tilt_rad))
    if cos_incidence <= 0:
        return 0.0

    beam = direct * cos_incidence / max(math.sin(elev_rad), 0.01)
    diff = diffuse or 0.0
    ground = ghi * 0.2 * (1 - math.cos(tilt_rad)) / 2
    return max(0.0, beam + diff * (1 + math.cos(tilt_rad)) / 2 + ground)


def temperature_factor(temp_c: float | None) -> float:
    if temp_c is None:
        return 1.0
    delta = temp_c - REFERENCE_TEMP_C
    return max(0.5, 1.0 + TEMP_COEFFICIENT_PER_C * delta)


def baseline_power_w(
    point: WeatherForecastPoint,
    site: SolarSiteConfiguration,
) -> float:
    """Compute baseline AC power in watts from weather and site config."""
    if not site.enabled or site.installed_peak_power_kw <= 0:
        return 0.0

    irr = irradiance_wm2(point, site)
    if irr <= 0:
        return 0.0

    loss = max(0.0, min(50.0, site.system_loss_percent)) / 100.0
    temp_f = temperature_factor(point.temperature_c)

    # Standard: P = kWp * (G/1000) * temp_factor * (1 - losses)
    power_kw = site.installed_peak_power_kw * (irr / 1000.0) * temp_f * (1.0 - loss)
    power_w = max(0.0, power_kw * 1000.0)

    if site.inverter_max_power_kw is not None and site.inverter_max_power_kw > 0:
        power_w = min(power_w, site.inverter_max_power_kw * 1000.0)

    return power_w


def baseline_energy_kwh(power_w: float) -> float:
    return (power_w / 1000.0) * INTERVAL_HOURS


def _solar_geometry(ts: datetime, lat: float, lon: float, timezone: str = "UTC") -> tuple[float, float]:
    """Return (elevation_deg, azimuth_deg) simplified solar position."""
    from datetime import UTC
    from zoneinfo import ZoneInfo

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    local = ts.astimezone(ZoneInfo(timezone))

    day_of_year = local.timetuple().tm_yday
    hour = local.hour + local.minute / 60.0 + local.second / 3600.0
    # Solar declination (Cooper)
    decl = 23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    hour_angle = math.radians(15 * (hour - 12) + lon * 4 / 60)  # simplified

    sin_elev = math.sin(lat_rad) * math.sin(decl_rad) + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hour_angle)
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, sin_elev))))

    cos_az = (math.sin(decl_rad) - math.sin(lat_rad) * sin_elev) / max(math.cos(lat_rad) * math.cos(math.radians(elevation)), 1e-6)
    azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    if hour_angle > 0:
        azimuth = 360 - azimuth

    return elevation, azimuth
