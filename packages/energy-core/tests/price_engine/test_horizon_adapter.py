"""Tests for price engine horizon adapter."""

from datetime import UTC, datetime, timedelta

from energy_core.price_engine.horizon_adapter import (
    export_value_from_periods,
    price_by_hour_from_periods,
    price_by_period,
)
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
)


def _period(start: datetime, market: float, import_price: float, export_price: float) -> PricePeriod:
    return PricePeriod(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=market,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=export_price,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
    )


def test_price_by_period_aligns_to_15_min():
    start = datetime(2026, 8, 13, 10, 7, tzinfo=UTC)
    period = _period(start, 0.3, 1.1, 0.4)
    mapped = price_by_period((period,))
    assert datetime(2026, 8, 13, 10, 0, tzinfo=UTC) in mapped


def test_price_by_hour_converts_sek_to_eur():
    start = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    period = _period(start, 1.0, 2.0, 0.5)
    hourly = price_by_hour_from_periods((period,))
    hour_key = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    spot, all_in = hourly[hour_key]
    assert spot is not None and spot > 0
    assert all_in is not None and all_in > spot


def test_export_value_from_latest_period():
    start = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    periods = (
        _period(start, 0.3, 1.0, 0.35),
        _period(start + timedelta(hours=1), 0.4, 1.2, 0.42),
    )
    assert export_value_from_periods(periods) == 0.42
