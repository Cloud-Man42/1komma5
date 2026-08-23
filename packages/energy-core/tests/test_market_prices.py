"""Tests for Heartbeat market price parsing."""

from datetime import UTC, datetime, timedelta

from energy_core.heartbeat.market_prices import parse_market_prices


def _price_node(amount: float) -> dict:
    return {"price": {"amount": amount}}


def _v4_payload(
    *, timestamps: list[str], spot_prices: list[float], all_in_prices: list[float]
) -> dict:
    timeseries = {
        ts: {
            "marketPrice": spot,
            "marketPriceWithGridCostAndVat": all_in,
        }
        for ts, spot, all_in in zip(timestamps, spot_prices, all_in_prices, strict=True)
    }
    return {
        "energyMarket": {
            "averagePrice": _price_node(sum(spot_prices) / len(spot_prices)),
            "highestPrice": _price_node(max(spot_prices)),
            "lowestPrice": _price_node(min(spot_prices)),
        },
        "energyMarketWithGridCosts": {
            "averagePrice": _price_node(sum(all_in_prices) / len(all_in_prices)),
            "highestPrice": _price_node(max(all_in_prices)),
            "lowestPrice": _price_node(min(all_in_prices)),
        },
        "energyMarketWithGridCostsAndVat": {
            "averagePrice": _price_node(sum(all_in_prices) / len(all_in_prices)),
            "highestPrice": _price_node(max(all_in_prices)),
            "lowestPrice": _price_node(min(all_in_prices)),
        },
        "timeseries": timeseries,
        "gridCostsTotal": _price_node(0.12),
        "vat": 0.25,
        "usesFallbackGridCosts": False,
        "gridCostsComponents": {},
    }


def test_parse_v4_market_prices():
    now = datetime(2026, 8, 13, 18, tzinfo=UTC)
    timestamps = [
        (now + timedelta(hours=offset)).isoformat().replace("+00:00", "Z") for offset in range(3)
    ]
    payload = _v4_payload(
        timestamps=timestamps,
        spot_prices=[0.08, 0.12, 0.16],
        all_in_prices=[0.18, 0.22, 0.26],
    )

    parsed = parse_market_prices(payload)

    assert parsed.current_price_eur_kwh in {0.18, 0.22, 0.26}
    assert parsed.average_all_in_eur_kwh == 0.22
    assert parsed.highest_all_in_eur_kwh == 0.26
    assert parsed.lowest_all_in_eur_kwh == 0.18
    assert len(parsed.points) == 3
    assert parsed.points[0].spot_eur_kwh == 0.08
    assert parsed.points[1].all_in_eur_kwh == 0.22


def test_parse_legacy_market_prices():
    now = datetime(2026, 8, 13, 18, tzinfo=UTC)
    parsed = parse_market_prices(
        {
            "data": [
                {"timestamp": now.isoformat().replace("+00:00", "Z"), "price": 0.11},
                {
                    "timestamp": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                    "price": 0.09,
                },
            ]
        }
    )

    assert parsed.current_price_eur_kwh in {0.09, 0.11}
    assert len(parsed.points) == 2
    assert parsed.lowest_all_in_eur_kwh == 0.09


def test_parse_empty_market_prices():
    parsed = parse_market_prices(None)
    assert parsed.points == ()
    assert parsed.current_price_eur_kwh is None
