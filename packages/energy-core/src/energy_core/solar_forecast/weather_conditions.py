"""WMO weather code interpretation and current-conditions extraction (Swedish)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint

# WMO 4677 weather codes as delivered by Open-Meteo.
WMO_CONDITIONS: dict[int, tuple[str, str]] = {
    0: ("Klart", "clear"),
    1: ("Mestadels klart", "mostly-clear"),
    2: ("Delvis molnigt", "partly-cloudy"),
    3: ("Mulet", "overcast"),
    45: ("Dimma", "fog"),
    48: ("Underkyld dimma", "fog"),
    51: ("Lätt duggregn", "drizzle"),
    53: ("Duggregn", "drizzle"),
    55: ("Kraftigt duggregn", "drizzle"),
    56: ("Underkylt duggregn", "drizzle"),
    57: ("Kraftigt underkylt duggregn", "drizzle"),
    61: ("Lätt regn", "rain"),
    63: ("Regn", "rain"),
    65: ("Kraftigt regn", "rain"),
    66: ("Underkylt regn", "rain"),
    67: ("Kraftigt underkylt regn", "rain"),
    71: ("Lätt snöfall", "snow"),
    73: ("Snöfall", "snow"),
    75: ("Kraftigt snöfall", "snow"),
    77: ("Snökorn", "snow"),
    80: ("Lätta regnskurar", "showers"),
    81: ("Regnskurar", "showers"),
    82: ("Kraftiga regnskurar", "showers"),
    85: ("Lätta snöbyar", "snow"),
    86: ("Kraftiga snöbyar", "snow"),
    95: ("Åska", "thunder"),
    96: ("Åska med hagel", "thunder"),
    99: ("Kraftig åska med hagel", "thunder"),
}

CLOUD_FALLBACK_CONDITIONS: tuple[tuple[float, str, str], ...] = (
    (12.5, "Klart", "clear"),
    (37.5, "Mestadels klart", "mostly-clear"),
    (75.0, "Delvis molnigt", "partly-cloudy"),
    (100.0, "Mulet", "overcast"),
)


def describe_weather_code(code: int | None, cloud_cover_pct: float | None = None) -> tuple[str, str]:
    """Swedish label and icon key for a WMO code, falling back to cloud cover."""
    if code is not None and code in WMO_CONDITIONS:
        return WMO_CONDITIONS[code]
    if cloud_cover_pct is not None:
        for threshold, label, icon in CLOUD_FALLBACK_CONDITIONS:
            if cloud_cover_pct <= threshold:
                return label, icon
        return "Mulet", "overcast"
    return "Okänt", "unknown"


def solar_impact_sv(cloud_cover_pct: float | None) -> str:
    """Human explanation of how current cloud cover affects production."""
    if cloud_cover_pct is None:
        return "Molntäcke okänt — prognosen kan vara osäker"
    if cloud_cover_pct < 20:
        return "Goda solförhållanden — nära full produktion"
    if cloud_cover_pct < 50:
        return "Lätt molnighet — något lägre produktion"
    if cloud_cover_pct < 80:
        return "Molnigt — märkbart lägre produktion"
    return "Mulet — kraftigt reducerad produktion"


@dataclass(frozen=True, slots=True)
class CurrentWeather:
    timestamp: datetime
    temperature_c: float | None
    cloud_cover_pct: float | None
    wind_speed_ms: float | None
    relative_humidity_pct: float | None
    precipitation_mm: float | None
    ghi_wm2: float | None
    weather_code: int | None
    condition_sv: str
    condition_icon: str
    solar_impact_sv: str


def nearest_point(
    points: tuple[WeatherForecastPoint, ...] | list[WeatherForecastPoint],
    now: datetime,
) -> WeatherForecastPoint | None:
    """Weather point closest in time to `now`, ignoring points far in the past."""
    if not points:
        return None
    candidates = [p for p in points if p.timestamp >= now - timedelta(hours=3)]
    pool = candidates or list(points)
    return min(pool, key=lambda p: abs((p.timestamp - now).total_seconds()))


def build_current_weather(weather: WeatherForecast, *, now: datetime) -> CurrentWeather | None:
    """Extract the observation closest to now, enriched with Swedish descriptions."""
    point = nearest_point(weather.points, now)
    if point is None:
        return None

    label, icon = describe_weather_code(point.weather_code, point.cloud_cover_pct)
    return CurrentWeather(
        timestamp=point.timestamp,
        temperature_c=_round(point.temperature_c, 1),
        cloud_cover_pct=_round(point.cloud_cover_pct, 0),
        wind_speed_ms=_round(point.wind_speed_ms, 1),
        relative_humidity_pct=_round(point.relative_humidity_pct, 0),
        precipitation_mm=_round(point.precipitation_mm, 1),
        ghi_wm2=_round(point.ghi_wm2, 0),
        weather_code=point.weather_code,
        condition_sv=label,
        condition_icon=icon,
        solar_impact_sv=solar_impact_sv(point.cloud_cover_pct),
    )


def hourly_weather_series(
    weather: WeatherForecast,
    *,
    now: datetime,
    hours: int = 24,
) -> list[WeatherForecastPoint]:
    """One point per hour from the start of the current hour, for chart rendering."""
    if not weather.points:
        return []

    start = now.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=hours)
    buckets: dict[datetime, WeatherForecastPoint] = {}

    for point in weather.points:
        if point.timestamp < start or point.timestamp >= end:
            continue
        hour = point.timestamp.replace(minute=0, second=0, microsecond=0)
        existing = buckets.get(hour)
        if existing is None or point.timestamp < existing.timestamp:
            buckets[hour] = point

    return [buckets[key] for key in sorted(buckets)]


def _round(value: float | None, digits: int) -> float | None:
    if value is None:
        return None
    return round(value, digits) if digits > 0 else float(round(value))
