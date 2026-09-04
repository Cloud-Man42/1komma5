"""Redis cache key helpers."""

from __future__ import annotations

from energy_core.cache.service import (
    financial_stats_cache_key,
    site_dashboard_cache_key,
    site_snapshot_cache_key,
    solar_forecast_cache_key,
    current_price_cache_key,
)


def test_site_snapshot_cache_key() -> None:
    assert site_snapshot_cache_key(3) == "emic:site:3:snapshot"


def test_site_dashboard_cache_key() -> None:
    assert site_dashboard_cache_key(3) == "emic:site:3:dashboard"


def test_financial_stats_cache_key() -> None:
    assert financial_stats_cache_key(3, "month", 2026) == "emic:site:3:financial:month:2026"
    assert financial_stats_cache_key(3, "day", None) == "emic:site:3:financial:day:all"


def test_solar_forecast_cache_key() -> None:
    assert solar_forecast_cache_key(3) == "emic:site:3:solar:forecast"


def test_current_price_cache_key() -> None:
    assert current_price_cache_key(3) == "emic:site:3:prices:current"
