"""Timezone-aware solar geometry service."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from energy_core.solar_intelligence.types import SolarGeometry


class SolarGeometryService:
    """Compute solar position using local solar time (DST-safe)."""

    def __init__(self, *, latitude: float, longitude: float, timezone: str) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone

    def elevation_azimuth(self, ts: datetime) -> tuple[float, float]:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        local = ts.astimezone(ZoneInfo(self.timezone))
        return _solar_position(local, self.latitude, self.longitude)

    def geometry_at(self, ts: datetime) -> SolarGeometry:
        elev, az = self.elevation_azimuth(ts)
        sunrise, sunset = self.sunrise_sunset(ts.date())
        day_len = 0.0
        if sunrise and sunset:
            day_len = (sunset - sunrise).total_seconds() / 3600.0
        return SolarGeometry(
            elevation_deg=elev,
            azimuth_deg=az,
            sunrise=sunrise,
            sunset=sunset,
            day_length_hours=day_len,
        )

    def sunrise_sunset(self, day: date) -> tuple[datetime | None, datetime | None]:
        tz = ZoneInfo(self.timezone)
        start = datetime.combine(day, time.min, tzinfo=tz)
        end = start + timedelta(days=1)
        step = timedelta(minutes=5)
        sunrise: datetime | None = None
        sunset: datetime | None = None
        prev_elev = -90.0
        cur = start
        while cur < end:
            elev, _ = _solar_position(cur, self.latitude, self.longitude)
            if prev_elev <= 0 < elev and sunrise is None:
                sunrise = cur
            if prev_elev > 0 >= elev and sunset is None and sunrise is not None:
                sunset = cur
                break
            prev_elev = elev
            cur += step
        return sunrise, sunset

    def is_daylight(self, ts: datetime, *, min_elevation_deg: float = 5.0) -> bool:
        elev, _ = self.elevation_azimuth(ts)
        return elev > min_elevation_deg


def _solar_position(local_ts: datetime, lat: float, lon: float) -> tuple[float, float]:
    """NOAA-style simplified solar position in local time."""
    day_of_year = local_ts.timetuple().tm_yday
    hour = local_ts.hour + local_ts.minute / 60.0 + local_ts.second / 3600.0

    decl = 23.45 * math.sin(math.radians(360.0 / 365.0 * (day_of_year - 81)))
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)

    # Local solar time approximation
    tz_offset_hours = local_ts.utcoffset().total_seconds() / 3600.0 if local_ts.utcoffset() else 0.0
    solar_time = hour + (lon / 15.0) - tz_offset_hours
    hour_angle = math.radians(15.0 * (solar_time - 12.0))

    sin_elev = math.sin(lat_rad) * math.sin(decl_rad) + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hour_angle)
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, sin_elev))))

    if elevation <= -0.5:
        return elevation, 0.0

    cos_az = (math.sin(decl_rad) - math.sin(lat_rad) * sin_elev) / max(
        math.cos(lat_rad) * math.cos(math.radians(max(elevation, 0.01))), 1e-6
    )
    azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    if hour_angle > 0:
        azimuth = 360.0 - azimuth
    return elevation, azimuth
