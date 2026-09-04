"""Tests for Heartbeat price providers."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from energy_core.export_revenue.calculator import SellPriceConfig
from energy_core.price_engine.providers.heartbeat_export import HeartbeatExportPriceProvider
from energy_core.price_engine.providers.heartbeat_market import (
    HeartbeatMarketPriceProvider,
    _import_points_from_payload,
    _market_points_from_payload,
)


def _v4_payload():
    now = datetime(2026, 8, 13, 10, tzinfo=UTC)
    timestamps = [(now + timedelta(hours=i)).isoformat().replace("+00:00", "Z") for i in range(2)]
    spot = [0.08, 0.09]
    all_in = [0.20, 0.21]

    def _price_node(amount: float) -> dict:
        return {"price": {"amount": amount}}

    timeseries = {
        ts: {
            "marketPrice": s,
            "marketPriceWithGridCostAndVat": a,
        }
        for ts, s, a in zip(timestamps, spot, all_in, strict=True)
    }
    return {
        "energyMarket": {
            "averagePrice": _price_node(sum(spot) / len(spot)),
            "highestPrice": _price_node(max(spot)),
            "lowestPrice": _price_node(min(spot)),
        },
        "energyMarketWithGridCosts": {
            "averagePrice": _price_node(sum(all_in) / len(all_in)),
            "highestPrice": _price_node(max(all_in)),
            "lowestPrice": _price_node(min(all_in)),
        },
        "energyMarketWithGridCostsAndVat": {
            "averagePrice": _price_node(sum(all_in) / len(all_in)),
            "highestPrice": _price_node(max(all_in)),
            "lowestPrice": _price_node(min(all_in)),
        },
        "timeseries": timeseries,
        "gridCostsTotal": _price_node(0.02),
        "vat": 0.25,
        "usesFallbackGridCosts": False,
        "gridCostsComponents": {},
    }


def test_market_points_from_hourly_payload():
    points = _market_points_from_payload(_v4_payload(), resolution="1h")
    assert len(points) == 2
    assert points[0].native_resolution_minutes == 60
    assert points[0].market_price_eur_kwh == pytest.approx(0.08)


def test_import_points_include_all_in():
    points = _import_points_from_payload(_v4_payload(), resolution="1h")
    assert points[0].import_price_eur_kwh == pytest.approx(0.20)


@pytest.mark.asyncio
async def test_export_provider_uses_sell_config():
    client = AsyncMock()
    client.fetch_market_prices.return_value = _v4_payload()
    client.fetch_heartbeat_prices.return_value = {"feedInTariff": {"amount": 0.05}}

    provider = HeartbeatExportPriceProvider(client)
    points = await provider.fetch(
        system_id="sys-1",
        from_iso="2026-08-13T00:00:00Z",
        to_iso="2026-08-14T00:00:00Z",
        sell_config=SellPriceConfig(pricing_mode="spot"),
        resolution="1h",
    )
    assert len(points) == 2
    assert points[0].export_price_eur_kwh is not None


@pytest.mark.asyncio
async def test_market_provider_delegates_to_client():
    client = AsyncMock()
    client.fetch_market_prices.return_value = _v4_payload()
    provider = HeartbeatMarketPriceProvider(client)
    points = await provider.fetch(
        system_id="sys-1",
        from_iso="2026-08-13T00:00:00Z",
        to_iso="2026-08-14T00:00:00Z",
        resolution="1h",
    )
    assert len(points) == 2
    client.fetch_market_prices.assert_awaited_once()
