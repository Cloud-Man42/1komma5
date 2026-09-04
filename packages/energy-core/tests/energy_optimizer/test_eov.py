"""Tests for EOV optimizer."""

from datetime import UTC, datetime, timedelta

import pytest

from energy_core.energy_optimizer.eov import compute_eov_decision, estimate_shiftable_savings
from energy_core.energy_optimizer.types import EnergyAction, EovConfig
from energy_core.price_engine.types import (
    Currency,
    PriceArea,
    PricePeriod,
    PriceQuality,
    PriceSource,
    StrategyState,
)


def _period(start: datetime, import_price: float, export_price: float = 0.39) -> PricePeriod:
    return PricePeriod(
        period_start=start,
        period_end=start + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=import_price * 0.25,
        import_price_sek_kwh=import_price,
        export_price_sek_kwh=export_price,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.REAL,
        is_estimated=False,
    )


def test_store_battery_when_future_peak_is_high():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    current = _period(now, import_price=0.8)
    future = tuple(_period(now + timedelta(hours=h), import_price=price) for h, price in ((4, 2.8), (5, 3.1)))
    decision = compute_eov_decision(
        current=current,
        horizon=(current, *future),
        battery_soc_pct=55.0,
        now=now,
    )
    assert decision is not None
    assert decision.action == EnergyAction.STORE_IN_BATTERY
    assert decision.strategy_state == StrategyState.SAVE_BATTERY
    assert decision.confidence >= 0.7


def test_export_when_export_beats_store():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    current = _period(now, import_price=0.5, export_price=1.6)
    future = tuple(_period(now + timedelta(hours=h), import_price=0.55) for h in range(1, 4))
    decision = compute_eov_decision(
        current=current,
        horizon=(current, *future),
        battery_soc_pct=60.0,
        now=now,
    )
    assert decision is not None
    assert decision.action == EnergyAction.EXPORT_TO_GRID
    assert decision.strategy_state == StrategyState.EXPORT


def test_missing_import_returns_none():
    now = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
    current = PricePeriod(
        period_start=now,
        period_end=now + timedelta(minutes=15),
        site_id=1,
        price_area=PriceArea.SE4,
        currency=Currency.SEK,
        market_price_sek_kwh=0.3,
        import_price_sek_kwh=None,
        export_price_sek_kwh=0.39,
        source=PriceSource.HEARTBEAT,
        quality=PriceQuality.MISSING,
        is_estimated=False,
    )
    assert compute_eov_decision(current=current, horizon=(current,), battery_soc_pct=50.0, now=now) is None


def test_estimate_shiftable_savings():
    now = datetime(2026, 8, 13, 0, 0, tzinfo=UTC)
    horizon = tuple(_period(now + timedelta(hours=h), import_price=price) for h, price in enumerate([2.0, 1.0, 1.5, 0.5]))
    saving = estimate_shiftable_savings(horizon, config=EovConfig(shiftable_kwh_per_day=10.0))
    assert saving == pytest.approx(7.5)
