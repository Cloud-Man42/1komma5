"""Smart charging schedule from spot price forecast."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

# Matches frontend PriceChart green bars (value <= average * ratio).
GREEN_PRICE_RATIO = 0.85


def should_charge_smart(
    now: datetime,
    *,
    departure_time: str | None,
    price_forecast: tuple[tuple[datetime, float], ...],
    current_price: float | None,
    expensive_threshold: float,
    charge_hours: float = 4.0,
    timezone: str = "Europe/Stockholm",
) -> tuple[bool, str]:
    """Decide whether to charge now based on price forecast and departure."""
    if current_price is not None and current_price <= expensive_threshold:
        return True, "cheap_now"

    if not price_forecast:
        if current_price is not None and current_price > expensive_threshold:
            return False, "expensive_no_forecast"
        return False, "no_forecast"

    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    window_end = _window_end(now, departure_time, timezone)
    slots = _hourly_slots(price_forecast, now, window_end)
    if not slots:
        if current_price is not None and current_price <= expensive_threshold:
            return True, "cheap_now"
        return False, "no_forecast_in_window"

    if current_price is not None:
        average = _average_price(slots)
        if average is not None and _is_green_price(current_price, average):
            return True, "cheap_now"
        min_price = min(price for _, price in slots)
        if current_price <= min_price + 0.001:
            return True, "cheap_now"

    hours_needed = max(1, int(charge_hours + 0.999))
    cheapest = sorted(slots, key=lambda item: item[1])[:hours_needed]
    cheapest_hours = {_hour_key(ts) for ts, _ in cheapest}

    current_hour = _hour_key(now)
    if current_hour in cheapest_hours:
        return True, "smart_scheduled"

    if current_price is not None and current_price <= expensive_threshold:
        return True, "cheap_now"

    return False, "smart_wait_cheaper"


def should_charge_by_price(
    now: datetime,
    *,
    price_forecast: tuple[tuple[datetime, float], ...],
    current_price: float | None,
    expensive_threshold: float,
    charge_hours: float = 4.0,
) -> tuple[bool, str]:
    """Price-only schedule — ignores departure and deadline constraints."""
    return should_charge_smart(
        now,
        departure_time=None,
        price_forecast=price_forecast,
        current_price=current_price,
        expensive_threshold=expensive_threshold,
        charge_hours=charge_hours,
    )


def _average_price(slots: list[tuple[datetime, float]]) -> float | None:
    if not slots:
        return None
    return sum(price for _, price in slots) / len(slots)


def _is_green_price(current_price: float, average_price: float) -> bool:
    return current_price <= average_price * GREEN_PRICE_RATIO


def _window_end(now: datetime, departure_time: str | None, timezone: str) -> datetime:
    horizon = now + timedelta(hours=24)
    if not departure_time:
        return horizon
    try:
        departure = _next_departure(now, departure_time, timezone)
    except (ValueError, KeyError):
        return horizon
    return min(departure, horizon)


def _next_departure(now: datetime, departure_hhmm: str, timezone: str) -> datetime:
    hour, minute = map(int, departure_hhmm.split(":"))
    tz = ZoneInfo(timezone)
    local_now = now.astimezone(tz)
    departure = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if departure <= local_now:
        departure += timedelta(days=1)
    return departure.astimezone(UTC)


def _hourly_slots(
    forecast: tuple[tuple[datetime, float], ...],
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, float]]:
    by_hour: dict[datetime, float] = {}
    for ts, price in forecast:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts < start or ts > end:
            continue
        key = _hour_key(ts)
        if key not in by_hour or price < by_hour[key]:
            by_hour[key] = price
    return [(hour, price) for hour, price in sorted(by_hour.items())]


def _hour_key(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
