from datetime import UTC, datetime, timedelta

import pytest

from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint
from energy_core.solar_forecast.weather_conditions import (
    build_current_weather,
    describe_weather_code,
    hourly_weather_series,
    nearest_point,
    solar_impact_sv,
)

NOW = datetime(2026, 8, 27, 10, 0, tzinfo=UTC)


def _point(offset_minutes: int, **kwargs) -> WeatherForecastPoint:
    defaults = {
        "ghi_wm2": 500.0,
        "cloud_cover_pct": 10.0,
        "temperature_c": 18.4,
        "wind_speed_ms": 3.1,
        "relative_humidity_pct": 52.0,
        "precipitation_mm": 0.0,
        "weather_code": 0,
    }
    defaults.update(kwargs)
    return WeatherForecastPoint(timestamp=NOW + timedelta(minutes=offset_minutes), **defaults)


def _forecast(points) -> WeatherForecast:
    return WeatherForecast(
        site_id=1,
        fetched_at=NOW,
        provider="open-meteo",
        points=tuple(points),
    )


def test_describe_weather_code_known_codes():
    assert describe_weather_code(0) == ("Klart", "clear")
    assert describe_weather_code(3) == ("Mulet", "overcast")
    assert describe_weather_code(95) == ("Åska", "thunder")


def test_describe_weather_code_falls_back_to_cloud_cover():
    assert describe_weather_code(None, 5.0) == ("Klart", "clear")
    assert describe_weather_code(None, 60.0) == ("Delvis molnigt", "partly-cloudy")
    assert describe_weather_code(None, 95.0) == ("Mulet", "overcast")


def test_describe_weather_code_unknown_without_cloud_data():
    assert describe_weather_code(None, None) == ("Okänt", "unknown")
    assert describe_weather_code(12345, None) == ("Okänt", "unknown")


@pytest.mark.parametrize(
    ("cloud", "expected_fragment"),
    [
        (0.0, "Goda solförhållanden"),
        (35.0, "Lätt molnighet"),
        (65.0, "Molnigt"),
        (95.0, "Mulet"),
        (None, "okänt"),
    ],
)
def test_solar_impact_covers_all_bands(cloud, expected_fragment):
    assert expected_fragment in solar_impact_sv(cloud)


def test_nearest_point_prefers_closest_future_point():
    points = [_point(-30), _point(10), _point(120)]
    assert nearest_point(points, NOW).timestamp == NOW + timedelta(minutes=10)


def test_nearest_point_ignores_stale_history_but_keeps_pool_nonempty():
    stale = [_point(-600), _point(-700)]
    assert nearest_point(stale, NOW).timestamp == NOW - timedelta(minutes=600)


def test_nearest_point_empty_returns_none():
    assert nearest_point([], NOW) is None


def test_build_current_weather_maps_all_fields():
    current = build_current_weather(_forecast([_point(0)]), now=NOW)
    assert current is not None
    assert current.temperature_c == 18.4
    assert current.wind_speed_ms == 3.1
    assert current.relative_humidity_pct == 52.0
    assert current.cloud_cover_pct == 10.0
    assert current.ghi_wm2 == 500.0
    assert current.condition_sv == "Klart"
    assert current.condition_icon == "clear"
    assert "Goda solförhållanden" in current.solar_impact_sv


def test_build_current_weather_without_points_returns_none():
    assert build_current_weather(_forecast([]), now=NOW) is None


def test_build_current_weather_handles_missing_measurements():
    point = WeatherForecastPoint(timestamp=NOW)
    current = build_current_weather(_forecast([point]), now=NOW)
    assert current is not None
    assert current.temperature_c is None
    assert current.wind_speed_ms is None
    assert current.condition_sv == "Okänt"


def test_hourly_weather_series_one_point_per_hour():
    points = [_point(minutes) for minutes in (0, 15, 30, 45, 60, 75, 120)]
    series = hourly_weather_series(_forecast(points), now=NOW, hours=24)
    assert [p.timestamp for p in series] == [
        NOW,
        NOW + timedelta(hours=1),
        NOW + timedelta(hours=2),
    ]


def test_hourly_weather_series_excludes_points_outside_window():
    points = [_point(-120), _point(0), _point(60 * 30)]
    series = hourly_weather_series(_forecast(points), now=NOW, hours=4)
    assert [p.timestamp for p in series] == [NOW]


def test_hourly_weather_series_empty_forecast():
    assert hourly_weather_series(_forecast([]), now=NOW) == []
