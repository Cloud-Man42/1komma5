"""Tests for SolarIntelligenceEngine hourly horizon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from energy_core.solar_intelligence.engine import SolarIntelligenceEngine
from energy_core.solar_intelligence.types import RadiationSample, WeatherSnapshot
from energy_core.solar_forecast.types import SolarSiteConfiguration


def _site() -> SolarSiteConfiguration:
    return SolarSiteConfiguration(
        site_id=1,
        latitude=55.6,
        longitude=13.0,
        timezone="Europe/Stockholm",
        installed_peak_power_kw=8.0,
        tilt_deg=35.0,
        azimuth_deg=180.0,
        system_loss_percent=10.0,
        inverter_max_power_kw=8.0,
    )


def _radiation_rows(from_ts: datetime, hours: int) -> list[RadiationSample]:
    rows: list[RadiationSample] = []
    for i in range(hours):
        ts = from_ts + timedelta(hours=i)
        ghi = 500.0 if 8 <= ts.astimezone(UTC).hour <= 16 else 0.0
        rows.append(RadiationSample(ts_utc=ts, parameter="ghi", value_wm2=ghi))
        rows.append(RadiationSample(ts_utc=ts, parameter="dni", value_wm2=400.0))
        rows.append(RadiationSample(ts_utc=ts, parameter="dhi", value_wm2=100.0))
    return rows


def _weather_rows(from_ts: datetime, hours: int) -> list[WeatherSnapshot]:
    return [
        WeatherSnapshot(
            ts_utc=from_ts + timedelta(hours=i),
            temperature_c=18.0,
            cloud_cover_pct=20.0,
        )
        for i in range(hours)
    ]


@pytest.mark.asyncio
async def test_generate_includes_past_hours_for_local_today():
    now = datetime(2026, 8, 29, 8, 40, tzinfo=UTC)
    local_day_start = datetime(2026, 8, 28, 22, 0, tzinfo=UTC)

    radiation = AsyncMock()
    weather = AsyncMock()
    radiation.fetch_radiation = AsyncMock(return_value=_radiation_rows(local_day_start, 48))
    weather.fetch_weather = AsyncMock(return_value=_weather_rows(local_day_start, 48))
    radiation.provider_name = "test"

    engine = SolarIntelligenceEngine(radiation_provider=radiation, weather_provider=weather, horizon_hours=48)
    forecast = await engine.generate(_site(), now=now)

    assert forecast.hourly
    assert min(p.timestamp for p in forecast.hourly) < now
    assert any(p.timestamp < now for p in forecast.hourly)

    radiation.fetch_radiation.assert_awaited_once()
    call_kwargs = radiation.fetch_radiation.await_args.kwargs
    assert call_kwargs["from_ts"] == local_day_start
