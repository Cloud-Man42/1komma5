"""Tests for smart charging schedule."""

from datetime import UTC, datetime, timedelta

from energy_core.charging.smart_schedule import should_charge_by_price, should_charge_smart


def _forecast(*prices: tuple[str, float]) -> tuple[tuple[datetime, float], ...]:
    base = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    return tuple(
        (base + timedelta(hours=index), price)
        for index, (_, price) in enumerate(prices)
    )


def test_cheap_now_charges_immediately():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    charge, reason = should_charge_smart(
        now,
        departure_time="07:00",
        price_forecast=(),
        current_price=0.20,
        expensive_threshold=0.35,
    )
    assert charge is True
    assert reason == "cheap_now"


def test_expensive_now_waits_for_cheaper_slot():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.55),
        (now + timedelta(hours=1), 0.55),
        (now + timedelta(hours=2), 0.12),
        (now + timedelta(hours=3), 0.15),
        (now + timedelta(hours=4), 0.18),
        (now + timedelta(hours=5), 0.20),
    )
    charge, reason = should_charge_smart(
        now,
        departure_time="20:00",
        price_forecast=forecast,
        current_price=0.55,
        expensive_threshold=0.35,
        charge_hours=4,
        timezone="Europe/Stockholm",
    )
    assert charge is False
    assert reason == "smart_wait_cheaper"


def test_scheduled_cheapest_hour_charges():
    now = datetime(2026, 8, 14, 14, 0, tzinfo=UTC)
    forecast = (
        (now - timedelta(hours=2), 0.55),
        (now - timedelta(hours=1), 0.50),
        (now, 0.12),
        (now + timedelta(hours=1), 0.15),
        (now + timedelta(hours=2), 0.18),
        (now + timedelta(hours=3), 0.55),
    )
    charge, reason = should_charge_smart(
        now,
        departure_time="20:00",
        price_forecast=forecast,
        current_price=0.40,
        expensive_threshold=0.35,
        charge_hours=3,
        timezone="Europe/Stockholm",
    )
    assert charge is True
    assert reason == "smart_scheduled"


def test_green_price_tier_charges_even_if_not_in_top_n_cheapest():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.44),
        (now + timedelta(hours=1), 0.35),
        (now + timedelta(hours=2), 0.36),
        (now + timedelta(hours=3), 0.37),
        (now + timedelta(hours=4), 0.38),
        (now + timedelta(hours=5), 0.90),
        (now + timedelta(hours=6), 0.95),
    )
    charge, reason = should_charge_smart(
        now,
        departure_time="20:00",
        price_forecast=forecast,
        current_price=0.44,
        expensive_threshold=0.35,
        charge_hours=4,
        timezone="Europe/Stockholm",
    )
    assert charge is True
    assert reason == "cheap_now"


def test_current_minimum_price_charges():
    now = datetime(2026, 8, 14, 3, 0, tzinfo=UTC)
    forecast = (
        (now, 0.08),
        (now + timedelta(hours=1), 0.45),
        (now + timedelta(hours=2), 0.50),
        (now + timedelta(hours=3), 0.48),
    )
    charge, reason = should_charge_smart(
        now,
        departure_time="07:00",
        price_forecast=forecast,
        current_price=0.08,
        expensive_threshold=0.35,
        charge_hours=4,
        timezone="Europe/Stockholm",
    )
    assert charge is True
    assert reason == "cheap_now"


def test_no_forecast_expensive_pauses():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    charge, reason = should_charge_smart(
        now,
        departure_time="07:00",
        price_forecast=(),
        current_price=0.55,
        expensive_threshold=0.35,
    )
    assert charge is False
    assert reason == "expensive_no_forecast"


def test_price_mode_ignores_departure_window():
    now = datetime(2026, 8, 14, 12, 0, tzinfo=UTC)
    forecast = (
        (now, 0.55),
        (now + timedelta(hours=8), 0.10),
        (now + timedelta(hours=9), 0.12),
        (now + timedelta(hours=10), 0.14),
        (now + timedelta(hours=11), 0.16),
    )
    charge, reason = should_charge_by_price(
        now,
        price_forecast=forecast,
        current_price=0.55,
        expensive_threshold=0.35,
        charge_hours=4,
    )
    assert charge is False
    assert reason == "smart_wait_cheaper"
