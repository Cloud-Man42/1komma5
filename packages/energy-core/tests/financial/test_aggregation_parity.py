"""Parity tests between raw integration and daily aggregate paths."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.export_revenue.calculator import SellPriceConfig
from energy_core.financial.aggregation import (
    aggregate_daily_to_period_stats,
    build_price_maps,
    integrate_financial_daily_accumulators,
    integrate_financial_stats,
)


class _Reading:
    __slots__ = ("recorded_at", "solar_production_w", "consumption_w", "grid_import_w", "grid_export_w", "battery_power_w")

    def __init__(self, recorded_at, solar, consumption, imp, exp, battery):
        self.recorded_at = recorded_at
        self.solar_production_w = solar
        self.consumption_w = consumption
        self.grid_import_w = imp
        self.grid_export_w = exp
        self.battery_power_w = battery


class _Price:
    __slots__ = ("recorded_at", "spot_price_eur_kwh", "all_in_price_eur_kwh", "feed_in_price_eur_kwh")

    def __init__(self, recorded_at, spot, all_in, feed_in):
        self.recorded_at = recorded_at
        self.spot_price_eur_kwh = spot
        self.all_in_price_eur_kwh = all_in
        self.feed_in_price_eur_kwh = feed_in


def _sample_data():
    base = datetime(2025, 6, 1, 8, 0, tzinfo=UTC)
    readings = [
        _Reading(base, 3000, 1500, 0, 1500, -500),
        _Reading(base + timedelta(minutes=5), 3500, 1600, 0, 1900, -500),
        _Reading(base + timedelta(minutes=10), 3200, 1400, 200, 1600, 0),
    ]
    prices = [
        _Price(base.replace(minute=0), 0.12, 0.15, 0.10),
        _Price((base + timedelta(hours=1)).replace(minute=0), 0.11, 0.14, 0.09),
    ]
    return readings, prices


def test_daily_aggregate_matches_raw_for_day_period():
    readings, prices = _sample_data()
    purchase, spot, feed_in = build_price_maps(prices)
    config = SellPriceConfig(pricing_mode="spot")

    raw = integrate_financial_stats(
        readings,
        period="day",
        timezone="Europe/Stockholm",
        purchase_prices=purchase,
        spot_prices=spot,
        feed_in_prices=feed_in,
        fallback_purchase_price_sek_kwh=2.0,
        config=config,
    )
    daily = integrate_financial_daily_accumulators(
        readings,
        timezone="Europe/Stockholm",
        purchase_prices=purchase,
        spot_prices=spot,
        feed_in_prices=feed_in,
        fallback_purchase_price_sek_kwh=2.0,
        config=config,
    )
    aggregated = aggregate_daily_to_period_stats(list(daily.values()), period="day", config=config)

    assert len(raw) == len(aggregated) == 1
    r = raw[0]
    a = aggregated[0]
    assert r.period_start == a.period_start
    assert r.solar_self_consumed_kwh == a.solar_self_consumed_kwh
    assert r.battery_self_consumed_kwh == a.battery_self_consumed_kwh
    assert r.exported_kwh == a.exported_kwh
    assert r.imported_kwh == a.imported_kwh
    assert r.solar_savings_sek == a.solar_savings_sek
    assert r.battery_savings_sek == a.battery_savings_sek
    assert r.export_revenue_sek == a.export_revenue_sek
    assert r.grid_import_cost_sek == a.grid_import_cost_sek
    assert r.market_priced_fraction == a.market_priced_fraction
    assert r.uncontracted_exported_kwh == a.uncontracted_exported_kwh
