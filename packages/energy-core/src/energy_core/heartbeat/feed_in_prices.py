"""Parse Heartbeat contractual feed-in tariffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from onekommafive.models.analytics import HeartbeatPrices


@dataclass(frozen=True, slots=True)
class ParsedFeedInTariff:
    """Daily feed-in tariff from Heartbeat heartbeat-prices endpoint."""

    feed_in_tariff_eur_kwh: float | None
    effective_heartbeat_price_eur_kwh: float | None
    source: str


def _window_feed_in_tariff_eur(window) -> float | None:
    """Extract contractual feed-in tariff from a Heartbeat price window."""
    tariff = window.grid_feed_in_tariff_eur_per_kwh
    if tariff is not None and tariff > 0:
        return tariff

    raw_fi = (getattr(window, "raw", None) or {}).get("gridFeedIn") or {}
    price_node = raw_fi.get("price") or {}
    amount = price_node.get("amount")
    if amount is not None:
        return float(amount)
    nested = price_node.get("price") or {}
    nested_amount = nested.get("amount")
    if nested_amount is not None:
        return float(nested_amount)
    return None


def parse_feed_in_tariff(data: dict[str, Any] | None) -> ParsedFeedInTariff:
    """Extract the day-window contractual feed-in tariff."""
    if not data:
        return ParsedFeedInTariff(None, None, "missing")

    model = HeartbeatPrices.from_dict(data)
    day = model.day
    tariff = _window_feed_in_tariff_eur(day)
    if tariff is not None and tariff > 0:
        return ParsedFeedInTariff(tariff, day.heartbeat_price_eur_per_kwh, "heartbeat-prices-day")

    for label, window in (("week", model.week), ("month", model.month)):
        fallback = _window_feed_in_tariff_eur(window)
        if fallback is not None and fallback > 0:
            return ParsedFeedInTariff(fallback, window.heartbeat_price_eur_per_kwh, f"heartbeat-prices-{label}")

    return ParsedFeedInTariff(None, day.heartbeat_price_eur_per_kwh, "missing")
