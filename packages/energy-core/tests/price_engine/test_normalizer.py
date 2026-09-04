"""Tests for hourly -> 15-minute price normalization."""

from datetime import UTC, datetime

from energy_core.price_engine.normalizer import merge_period_layers, normalize_to_periods
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
    RawPricePoint,
)


def test_hourly_point_replicates_to_four_15min_periods():
    ts = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    points = (
        RawPricePoint(
            timestamp=ts,
            market_price_eur_kwh=0.08,
            import_price_eur_kwh=0.22,
            export_price_eur_kwh=0.05,
            native_resolution_minutes=60,
        ),
    )
    rows = normalize_to_periods(
        points,
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
    )
    assert len(rows) == 4
    assert all(row.is_estimated for row in rows)
    assert all(row.quality == PriceQuality.ESTIMATED for row in rows)
    assert all(row.source == PriceSource.REPLICATED_HOURLY for row in rows)
    assert rows[0].period_start == datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    assert rows[3].period_start == datetime(2026, 8, 13, 10, 45, tzinfo=UTC)


def test_native_15min_point_is_real():
    ts = datetime(2026, 8, 13, 10, 15, tzinfo=UTC)
    points = (
        RawPricePoint(
            timestamp=ts,
            market_price_eur_kwh=0.10,
            import_price_eur_kwh=0.24,
            native_resolution_minutes=15,
        ),
    )
    rows = normalize_to_periods(points, site_id=1, price_area=PriceArea.DK2)
    assert len(rows) == 1
    assert rows[0].is_estimated is False
    assert rows[0].quality == PriceQuality.REAL
    assert rows[0].price_area == PriceArea.DK2


def test_negative_market_price_preserved():
    ts = datetime(2026, 8, 13, 3, 0, tzinfo=UTC)
    points = (
        RawPricePoint(
            timestamp=ts,
            market_price_eur_kwh=-0.01,
            import_price_eur_kwh=0.05,
            native_resolution_minutes=60,
        ),
    )
    rows = normalize_to_periods(points, site_id=1, price_area=PriceArea.SE4)
    assert rows[0].market_price_sek_kwh is not None
    assert rows[0].market_price_sek_kwh < 0


def test_merge_period_layers_combines_import_export():
    start = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    market = (
        PricePeriod(
            period_start=start,
            period_end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            site_id=1,
            price_area=PriceArea.SE4,
            currency=Currency.SEK,
            market_price_sek_kwh=0.32,
            import_price_sek_kwh=None,
            export_price_sek_kwh=None,
            source=PriceSource.HEARTBEAT,
            quality=PriceQuality.REAL,
            is_estimated=False,
        ),
    )
    import_rows = (
        PricePeriod(
            period_start=start,
            period_end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            site_id=1,
            price_area=PriceArea.SE4,
            currency=Currency.SEK,
            market_price_sek_kwh=None,
            import_price_sek_kwh=1.21,
            export_price_sek_kwh=None,
            source=PriceSource.HEARTBEAT,
            quality=PriceQuality.CALCULATED,
            is_estimated=False,
            components={"vat": 0.25},
        ),
    )
    export_rows = (
        PricePeriod(
            period_start=start,
            period_end=datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
            site_id=1,
            price_area=PriceArea.SE4,
            currency=Currency.SEK,
            market_price_sek_kwh=None,
            import_price_sek_kwh=None,
            export_price_sek_kwh=0.39,
            source=PriceSource.HEARTBEAT,
            quality=PriceQuality.CALCULATED,
            is_estimated=False,
        ),
    )
    merged = merge_period_layers(market, import_rows, export_rows)
    assert len(merged) == 1
    assert merged[0].market_price_sek_kwh == 0.32
    assert merged[0].import_price_sek_kwh == 1.21
    assert merged[0].export_price_sek_kwh == 0.39
