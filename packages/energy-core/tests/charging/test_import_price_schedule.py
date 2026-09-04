"""Tests for import-price smart charging schedule."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.import_price_schedule import (
    has_import_prices,
    import_price_allows_immediate_grid_charge,
    should_charge_import_price,
)
from energy_core.price_engine.periods import align_period_start


def _forecast(now: datetime, prices: list[float]) -> tuple[tuple[datetime, float], ...]:
    return tuple(
        (align_period_start(now + timedelta(minutes=15 * i)), price)
        for i, price in enumerate(prices)
    )


def test_has_import_prices_requires_current_and_forecast():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = _forecast(now, [1.0, 1.1, 1.2, 1.3])
    assert has_import_prices(current_import_sek_kwh=1.0, import_forecast=forecast)
    assert not has_import_prices(current_import_sek_kwh=None, import_forecast=forecast)
    assert not has_import_prices(current_import_sek_kwh=1.0, import_forecast=())


def test_waits_when_current_period_is_expensive():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = _forecast(now, [2.0, 2.1, 0.4, 0.45, 0.42, 0.43, 1.8, 1.9])
    charge, reason = should_charge_import_price(
        now,
        current_period_start=align_period_start(now),
        current_import_sek_kwh=2.0,
        import_forecast=forecast,
        charge_hours=1.0,
    )
    assert charge is False
    assert reason == "import_wait_cheaper"


def test_charges_in_green_import_window():
    now = datetime(2026, 8, 14, 12, 30, tzinfo=UTC)
    forecast = _forecast(now - timedelta(minutes=30), [2.0, 2.1, 0.4, 0.45, 0.42, 0.43, 1.8, 1.9])
    charge, reason = should_charge_import_price(
        now,
        current_period_start=align_period_start(now),
        current_import_sek_kwh=0.45,
        import_forecast=forecast,
        charge_hours=1.0,
    )
    assert charge is True
    assert reason == "import_cheap_now"


def test_waits_when_import_price_is_normal_not_green():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = _forecast(now, [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0])
    charge, reason = should_charge_import_price(
        now,
        current_period_start=align_period_start(now),
        current_import_sek_kwh=1.0,
        import_forecast=forecast,
        charge_hours=1.0,
    )
    assert charge is False
    assert reason == "import_wait_cheaper"


def test_deadline_urgency_overrides_wait():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = _forecast(now, [2.0, 2.1, 0.4, 0.45, 0.42, 0.43, 1.8, 1.9])
    charge, reason = should_charge_import_price(
        now,
        current_period_start=align_period_start(now),
        current_import_sek_kwh=2.0,
        import_forecast=forecast,
        charge_hours=1.0,
        urgency=0.85,
    )
    assert charge is True
    assert reason == "import_deadline_risk"


def test_import_price_allows_immediate_grid_charge():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = _forecast(now, [2.0, 2.1, 0.4, 0.45, 0.42, 0.43, 1.8, 1.9])
    assert import_price_allows_immediate_grid_charge(
        current_import_sek_kwh=0.4,
        import_forecast=forecast,
        now=datetime(2026, 8, 14, 12, 30, tzinfo=UTC),
    )
    assert not import_price_allows_immediate_grid_charge(
        current_import_sek_kwh=2.0,
        import_forecast=forecast,
        now=now,
    )
