"""Open-Meteo adapter routing for today's forecast vs archive."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from energy_core.solar_intelligence.providers.open_meteo_adapter import OpenMeteoAdapter

TIMEZONE = "Europe/Stockholm"


def _adapter() -> tuple[OpenMeteoAdapter, MagicMock]:
    provider = MagicMock()
    provider.get_forecast = AsyncMock(return_value=MagicMock(points=[]))
    provider.get_historical = AsyncMock(return_value=MagicMock(points=[]))
    return OpenMeteoAdapter(provider), provider


def _local_day_start() -> tuple[datetime, datetime]:
    """Start of the current local day, in UTC, plus the current instant.

    Derived from the real clock because the adapter routes against
    ``datetime.now(UTC)``; hardcoding a date makes the test pass only on that day.
    """
    now = datetime.now(UTC)
    tz = ZoneInfo(TIMEZONE)
    day_start = datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz)
    return day_start.astimezone(UTC), now


async def _get_weather(adapter: OpenMeteoAdapter, from_ts: datetime, to_ts: datetime) -> None:
    await adapter._get_weather(
        latitude=55.6,
        longitude=13.0,
        from_ts=from_ts,
        to_ts=to_ts,
        timezone=TIMEZONE,
    )


@pytest.mark.asyncio
async def test_get_weather_uses_forecast_for_local_today_start():
    adapter, provider = _adapter()
    day_start, now = _local_day_start()

    await _get_weather(adapter, day_start, now)

    provider.get_forecast.assert_awaited_once()
    provider.get_historical.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_weather_uses_archive_for_a_range_entirely_before_today():
    adapter, provider = _adapter()
    day_start, _ = _local_day_start()

    await _get_weather(adapter, day_start - timedelta(days=2), day_start - timedelta(days=1))

    provider.get_historical.assert_awaited_once()
    provider.get_forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_weather_clamps_a_straddling_range_to_today():
    adapter, provider = _adapter()
    day_start, now = _local_day_start()

    await _get_weather(adapter, day_start - timedelta(days=1), now)

    provider.get_historical.assert_not_awaited()
    provider.get_forecast.assert_awaited_once()
    # The archive half is dropped: the forecast call starts at the local day.
    assert provider.get_forecast.await_args.args[1] == day_start
