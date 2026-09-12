"""GridX tariff price client and parsing tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.integrations.heartbeat.gridx_client import GridXClient, GridXCredentials


def test_parse_gridx_tariff_periods():
    payload = {
        "name": "Day/Night",
        "currency": "EUR",
        "from": "2026-09-12T00:00:00Z",
        "to": "2026-09-13T00:00:00Z",
        "periods": [
            {
                "from": "2026-09-12T00:00:00Z",
                "to": "2026-09-12T00:15:00Z",
                "offtakePrice": 0.22,
                "feedinPrice": 0.08,
            },
            {
                "from": "2026-09-12T00:15:00Z",
                "to": "2026-09-12T00:30:00Z",
                "offtakePrice": 0.30,
                "feedinPrice": 0.08,
            },
        ],
    }

    parsed = parse_market_prices(payload)

    assert len(parsed.points) == 2
    assert parsed.points[0].spot_eur_kwh == pytest.approx(0.22)
    assert parsed.points[1].all_in_eur_kwh == pytest.approx(0.30)
    assert parsed.average_all_in_eur_kwh == pytest.approx(0.26)


def test_parse_gridx_empty_tariff_periods():
    parsed = parse_market_prices(
        {
            "name": "Empty",
            "currency": "EUR",
            "from": "2026-09-12T00:00:00Z",
            "to": "2026-09-12T00:00:00Z",
            "periods": [],
        }
    )
    assert parsed.points == ()
    assert parsed.current_price_eur_kwh is None


@pytest.mark.asyncio
async def test_gridx_fetch_market_prices_passes_interval():
    client = GridXClient(GridXCredentials(api_url="https://api.gridx.de", api_token="token"))
    client._request = AsyncMock(  # noqa: SLF001
        return_value={"name": "Empty", "periods": []},
    )

    await client.fetch_market_prices(
        "sys-1",
        from_iso="2026-09-12T00:00:00Z",
        to_iso="2026-09-13T00:00:00Z",
        resolution="15m",
    )

    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/tariff/prices",
        params={
            "interval": "2026-09-12T00:00:00Z/2026-09-13T00:00:00Z",
            "step": "15m",
        },
    )


@pytest.mark.asyncio
async def test_gridx_fetch_market_prices_hourly_omits_step():
    client = GridXClient(GridXCredentials(api_url="https://api.gridx.de", api_token="token"))
    client._request = AsyncMock(return_value={"periods": []})  # noqa: SLF001

    await client.fetch_market_prices(
        "sys-1",
        from_iso="2026-09-12T00:00:00Z",
        to_iso="2026-09-13T00:00:00Z",
        resolution="1h",
    )

    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/tariff/prices",
        params={"interval": "2026-09-12T00:00:00Z/2026-09-13T00:00:00Z"},
    )
