from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from energy_core.db.repositories import SiteRepository


def _v4_market_payload() -> dict:
    now = datetime(2026, 8, 21, 8, tzinfo=UTC)
    timestamps = [
        now.isoformat().replace("+00:00", "Z"),
        (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
    ]
    spot = [0.11, 0.13]
    all_in = [0.14, 0.16]

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


@pytest.mark.asyncio
async def test_market_prices_requires_heartbeat(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        repo = SiteRepository(session)
        site = await repo.get_by_slug("akarp")
        assert site is not None
        site.external_system_id = "00000000-0000-0000-0000-000000000001"
        await session.commit()

    res = await ac.get("/api/sites/akarp/market-prices")
    assert res.status_code == 503


@pytest.mark.asyncio
async def test_market_prices_404(client):
    ac, _, _ = client
    res = await ac.get("/api/sites/unknown/market-prices")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_market_prices_missing_system_id(client):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("summer-house-denmark")
        assert site is not None
        site.external_system_id = None
        await session.commit()

    res = await ac.get("/api/sites/summer-house-denmark/market-prices")
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_market_prices_success(client, monkeypatch):
    ac, session_factory, _ = client
    async with session_factory() as session:
        site = await SiteRepository(session).get_by_slug("akarp")
        assert site is not None
        site.external_system_id = "00000000-0000-0000-0000-000000000001"
        await session.commit()

    mock_client = SimpleNamespace(
        fetch_market_prices=AsyncMock(return_value=_v4_market_payload()),
    )
    monkeypatch.setattr(
        "app.api.prices.create_heartbeat_client",
        AsyncMock(return_value=mock_client),
    )

    res = await ac.get("/api/sites/akarp/market-prices")
    assert res.status_code == 200
    body = res.json()
    assert body["current_price_eur_kwh"] is not None
    assert len(body["points"]) >= 1
