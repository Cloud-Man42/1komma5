"""Parse Heartbeat market price payloads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from onekommafive.models.prices import MarketPrices


@dataclass(frozen=True, slots=True)
class MarketPricePoint:
    timestamp: datetime
    spot_eur_kwh: float
    all_in_eur_kwh: float | None


@dataclass(frozen=True, slots=True)
class ParsedMarketPrices:
    current_price_eur_kwh: float | None
    average_all_in_eur_kwh: float | None
    highest_all_in_eur_kwh: float | None
    lowest_all_in_eur_kwh: float | None
    points: tuple[MarketPricePoint, ...]


def _parse_dt(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _legacy_points(data: dict[str, Any]) -> tuple[float | None, tuple[MarketPricePoint, ...]]:
    points: list[MarketPricePoint] = []
    current_price: float | None = None
    now = datetime.now(UTC)

    series = data.get("data") or data.get("prices") or data.get("values") or data
    if isinstance(series, list):
        for point in series:
            if not isinstance(point, dict):
                continue
            ts = _parse_dt(str(point.get("timestamp") or point.get("time") or point.get("from") or ""))
            price = point.get("price") or point.get("value")
            if ts is None or not isinstance(price, (int, float)):
                continue
            value = float(price)
            points.append(MarketPricePoint(timestamp=ts, spot_eur_kwh=value, all_in_eur_kwh=value))
            if current_price is None or abs((ts - now).total_seconds()) < 3600:
                current_price = value

    points.sort(key=lambda item: item.timestamp)
    return current_price, tuple(points)


def parse_market_prices(data: dict[str, Any] | None) -> ParsedMarketPrices:
    if not data:
        return ParsedMarketPrices(None, None, None, None, ())

    if "timeseries" in data and "energyMarket" in data:
        parsed = MarketPrices.from_dict(data)
        points: list[MarketPricePoint] = []
        for ts in sorted(parsed.prices.keys()):
            timestamp = _parse_dt(ts)
            if timestamp is None:
                continue
            spot = parsed.prices[ts]
            all_in = parsed.prices_with_grid_costs_and_vat.get(ts)
            points.append(
                MarketPricePoint(
                    timestamp=timestamp,
                    spot_eur_kwh=spot,
                    all_in_eur_kwh=all_in if all_in is not None else None,
                )
            )

        now = datetime.now(UTC)
        current = _closest_price(points, now)
        return ParsedMarketPrices(
            current_price_eur_kwh=current,
            average_all_in_eur_kwh=_nan_to_none(parsed.average_price_all_in),
            highest_all_in_eur_kwh=_nan_to_none(parsed.highest_price_all_in),
            lowest_all_in_eur_kwh=_nan_to_none(parsed.lowest_price_all_in),
            points=tuple(points),
        )

    current_price, points = _legacy_points(data)
    values = [point.all_in_eur_kwh or point.spot_eur_kwh for point in points]
    return ParsedMarketPrices(
        current_price_eur_kwh=current_price,
        average_all_in_eur_kwh=(sum(values) / len(values)) if values else None,
        highest_all_in_eur_kwh=max(values) if values else None,
        lowest_all_in_eur_kwh=min(values) if values else None,
        points=points,
    )


def _closest_price(points: list[MarketPricePoint], now: datetime) -> float | None:
    if not points:
        return None
    closest = min(points, key=lambda point: abs((point.timestamp - now).total_seconds()))
    return closest.all_in_eur_kwh or closest.spot_eur_kwh


def _nan_to_none(value: float) -> float | None:
    import math

    return None if math.isnan(value) else value
