"""Tests for Heartbeat feed-in tariff parsing."""

from __future__ import annotations

from energy_core.heartbeat.feed_in_prices import parse_feed_in_tariff


def _feed_in_window(*, tariff_eur: float, heartbeat_eur: float | None = None) -> dict:
    window = {
        "gridFeedIn": {
            "price": {"amount": tariff_eur, "currency": "EUR"},
        },
    }
    if heartbeat_eur is not None:
        window["heartbeatPrice"] = {"price": {"amount": heartbeat_eur, "currency": "EUR"}}
    return window


def test_parse_feed_in_from_day_window():
    payload = {
        "day": _feed_in_window(tariff_eur=0.075, heartbeat_eur=0.08),
        "week": {},
        "month": {},
    }
    parsed = parse_feed_in_tariff(payload)
    assert parsed.feed_in_tariff_eur_kwh == 0.075
    assert parsed.effective_heartbeat_price_eur_kwh == 0.08
    assert parsed.source == "heartbeat-prices-day"


def test_parse_feed_in_falls_back_to_week():
    payload = {
        "day": _feed_in_window(tariff_eur=0),
        "week": _feed_in_window(tariff_eur=0.07),
        "month": {},
    }
    parsed = parse_feed_in_tariff(payload)
    assert parsed.feed_in_tariff_eur_kwh == 0.07
    assert parsed.source == "heartbeat-prices-week"


def test_parse_feed_in_missing_payload():
    parsed = parse_feed_in_tariff(None)
    assert parsed.feed_in_tariff_eur_kwh is None
    assert parsed.source == "missing"
