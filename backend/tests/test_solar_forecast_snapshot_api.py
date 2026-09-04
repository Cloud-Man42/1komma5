"""Tests for solar forecast API snapshot read path."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from helpers import enable_solar_config
from energy_core.solar_forecast.api_response import payload_to_solar_forecast_response
from energy_core.solar_forecast.types import WeatherForecast, WeatherForecastPoint


def _sample_weather(site_id: int = 1) -> WeatherForecast:
    now = datetime.now(UTC)
    points = tuple(
        WeatherForecastPoint(
            timestamp=now,
            ghi_wm2=600.0,
            gti_wm2=550.0,
            cloud_cover_pct=20.0,
            temperature_c=18.0,
            weather_code=1,
            wind_speed_ms=3.1,
            relative_humidity_pct=52.0,
        )
        for _ in range(4)
    )
    return WeatherForecast(
        site_id=site_id,
        fetched_at=now,
        provider="test",
        points=points,
        source="live",
    )


@pytest.mark.asyncio
async def test_solar_forecast_serves_snapshot_without_refresh(client, monkeypatch):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")

    snapshot_payload = {
        "site_id": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": "solar-forecast-v2",
        "quality": "good",
        "weather_source": "cache",
        "expected_today_kwh": 12.5,
        "remaining_today_kwh": 4.0,
        "expected_tomorrow_kwh": 10.0,
        "peak_power_w": 5000.0,
        "peak_time": None,
        "confidence": 0.8,
        "lower_today_kwh": 10.0,
        "upper_today_kwh": 14.0,
        "weather_summary": "Molnigt",
        "actual_today_kwh": 8.0,
        "forecast_so_far_kwh": 6.0,
        "remaining_vs_expected_kwh": 4.5,
        "age_seconds": 120.0,
        "freshness": "FRESH",
        "stale": False,
        "points": [],
    }

    refresh_mock = AsyncMock(return_value=True)
    with (
        patch(
            "app.api.solar_forecast.load_solar_forecast_snapshot",
            new=AsyncMock(return_value=snapshot_payload),
        ),
        patch(
            "energy_core.solar_forecast.coordinator.SolarForecastCoordinator.refresh_site_now",
            refresh_mock,
        ),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast")

    assert res.status_code == 200
    body = res.json()
    assert body["expected_today_kwh"] == 12.5
    assert body["freshness"] == "FRESH"
    assert body["age_seconds"] == 120.0
    refresh_mock.assert_not_called()


@pytest.mark.asyncio
async def test_solar_forecast_stale_snapshot_still_returns_200(client):
    ac, _, _ = client
    await enable_solar_config(ac, "akarp")

    snapshot_payload = {
        "site_id": 1,
        "generated_at": "2026-09-03T08:00:00+00:00",
        "model_version": "solar-forecast-v2",
        "quality": "good",
        "weather_source": "cache",
        "expected_today_kwh": 9.0,
        "remaining_today_kwh": 0.0,
        "peak_power_w": 4000.0,
        "confidence": 0.5,
        "lower_today_kwh": 8.0,
        "upper_today_kwh": 10.0,
        "weather_summary": "Gammal",
        "age_seconds": 7200.0,
        "freshness": "STALE",
        "stale": True,
        "points": [],
    }

    with patch(
        "app.api.solar_forecast.load_solar_forecast_snapshot",
        new=AsyncMock(return_value=snapshot_payload),
    ):
        res = await ac.get("/api/sites/akarp/solar/forecast")

    assert res.status_code == 200
    body = res.json()
    assert body["freshness"] == "STALE"
    assert body["stale"] is True


def test_payload_to_response_maps_freshness_fields():
    from app.schemas import SolarForecastPointResponse, SolarForecastResponse

    payload = {
        "site_id": 1,
        "generated_at": "2026-09-03T12:00:00+00:00",
        "model_version": "v2",
        "quality": "ok",
        "weather_source": "cache",
        "expected_today_kwh": 1.0,
        "remaining_today_kwh": 0.5,
        "peak_power_w": 100.0,
        "confidence": 0.9,
        "lower_today_kwh": 0.8,
        "upper_today_kwh": 1.2,
        "weather_summary": "test",
        "age_seconds": 45.0,
        "freshness": "LIVE",
        "stale": False,
        "points": [],
    }
    response = payload_to_solar_forecast_response(payload, SolarForecastResponse, SolarForecastPointResponse)
    assert response.freshness == "LIVE"
    assert response.age_seconds == 45.0
    assert response.stale is False


@pytest.mark.asyncio
async def test_solar_forecast_uses_cache_on_second_request(client):
    from unittest.mock import AsyncMock, patch

    from energy_core.cache.service import reset_cache_service

    ac, _, _ = client
    await enable_solar_config(ac, "akarp")
    reset_cache_service()
    cached_payload = {
        "site_id": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": "solar-forecast-v2",
        "quality": "good",
        "weather_source": "cache",
        "expected_today_kwh": 12.5,
        "remaining_today_kwh": 8.0,
        "peak_power_w": 4200.0,
        "confidence": 0.85,
        "lower_today_kwh": 10.0,
        "upper_today_kwh": 14.0,
        "weather_summary": "Molnigt",
        "age_seconds": 30.0,
        "freshness": "LIVE",
        "stale": False,
        "points": [],
    }
    cache = AsyncMock()
    cache.get = AsyncMock(side_effect=[None, cached_payload])
    cache.get_or_set = AsyncMock(return_value=cached_payload)

    with patch("app.api.solar_forecast.get_cache_service", return_value=cache):
        first = await ac.get("/api/sites/akarp/solar/forecast")
        second = await ac.get("/api/sites/akarp/solar/forecast")

    assert first.status_code == 200
    assert second.status_code == 200
    assert cache.get.await_count == 2
    cache.get_or_set.assert_awaited_once()
