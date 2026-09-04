"""Heartbeat-backed market and import price providers."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.heartbeat_client import HeartbeatClient
from energy_core.price_engine.types import RawPricePoint


def _parse_dt(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolution_minutes(resolution: str) -> int:
    if resolution == "15m":
        return 15
    return 60


def _components_from_payload(data: dict) -> dict:
    components: dict = {}
    if "gridCostsTotal" in data:
        grid = data.get("gridCostsTotal")
        if isinstance(grid, dict) and "price" in grid:
            amount = grid["price"].get("amount")
            if amount is not None:
                components["grid_costs_total_eur_kwh"] = float(amount)
    if "vat" in data:
        components["vat_rate"] = data["vat"]
    if data.get("usesFallbackGridCosts") is not None:
        components["uses_fallback_grid_costs"] = bool(data["usesFallbackGridCosts"])
    return components


class HeartbeatMarketPriceProvider:
    def __init__(self, client: HeartbeatClient) -> None:
        self._client = client

    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]:
        raw = await self._client.fetch_market_prices(
            system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution=resolution,
        )
        return _market_points_from_payload(raw, resolution=resolution)


class HeartbeatImportPriceProvider:
    def __init__(self, client: HeartbeatClient) -> None:
        self._client = client

    async def fetch(
        self,
        *,
        system_id: str,
        from_iso: str,
        to_iso: str,
        resolution: str = "15m",
    ) -> tuple[RawPricePoint, ...]:
        raw = await self._client.fetch_market_prices(
            system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution=resolution,
        )
        return _import_points_from_payload(raw, resolution=resolution)


def _market_points_from_payload(data: dict, *, resolution: str) -> tuple[RawPricePoint, ...]:
    parsed = parse_market_prices(data)
    native = _resolution_minutes(resolution)
    components = _components_from_payload(data)
    points: list[RawPricePoint] = []
    for point in parsed.points:
        points.append(
            RawPricePoint(
                timestamp=point.timestamp,
                market_price_eur_kwh=point.spot_eur_kwh,
                native_resolution_minutes=native,
                components={"market": components},
            )
        )
    return tuple(points)


def _import_points_from_payload(data: dict, *, resolution: str) -> tuple[RawPricePoint, ...]:
    parsed = parse_market_prices(data)
    native = _resolution_minutes(resolution)
    components = _components_from_payload(data)

    # When Heartbeat v4 payload includes per-series breakdown in timeseries keys.
    timeseries = data.get("timeseries") or {}
    points: list[RawPricePoint] = []
    for point in parsed.points:
        ts_key = None
        for key in timeseries:
            if _parse_dt(key) == point.timestamp:
                ts_key = key
                break
        row_components = dict(components)
        if ts_key and isinstance(timeseries[ts_key], dict):
            entry = timeseries[ts_key]
            if "marketPrice" in entry:
                mp = entry["marketPrice"]
                if isinstance(mp, dict) and "price" in mp:
                    row_components["market_price_eur_kwh"] = mp["price"].get("amount")
            if "marketPriceWithGridCostAndVat" in entry:
                ai = entry["marketPriceWithGridCostAndVat"]
                if isinstance(ai, dict) and "price" in ai:
                    row_components["all_in_price_eur_kwh"] = ai["price"].get("amount")

        points.append(
            RawPricePoint(
                timestamp=point.timestamp,
                import_price_eur_kwh=point.all_in_eur_kwh or point.spot_eur_kwh,
                native_resolution_minutes=native,
                components={"import": row_components},
            )
        )
    return tuple(points)
