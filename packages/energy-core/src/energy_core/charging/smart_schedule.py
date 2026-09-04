"""Smart charging schedule from spot price forecast."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

# Matches frontend PriceChart green bars (value <= average * ratio).
GREEN_PRICE_RATIO = 0.85
# Matches dashboard "red" tier — clearly expensive hours.
RED_PRICE_RATIO = 1.15

ScheduleMode = Literal["none", "departure", "deadline"]


def should_charge_smart(
    now: datetime,
    *,
    departure_time: str | None,
    price_forecast: tuple[tuple[datetime, float], ...],
    current_price: float | None,
    expensive_threshold: float,
    charge_hours: float = 4.0,
    timezone: str = "Europe/Stockholm",
    schedule_mode: ScheduleMode = "departure",
    urgency: float = 0.0,
) -> tuple[bool, str]:
    """Decide whether to charge now based on price forecast, schedule and urgency."""
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

    average = _average_price(slots)
    if current_price is not None:
        if average is not None and _is_green_price(current_price, average):
            return True, "cheap_now"

    if schedule_mode == "none":
        return _everyday_schedule_decision(current_price, average)

    clamped_urgency = max(0.0, min(1.0, urgency))
    if clamped_urgency >= 0.8:
        return True, "deadline_risk"

    if clamped_urgency >= 0.4:
        return _balanced_urgency_decision(
            now,
            slots=slots,
            current_price=current_price,
            average=average,
            charge_hours=charge_hours,
            urgency=clamped_urgency,
        )

    return _green_price_decision(now, slots=slots)


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
        schedule_mode="departure",
    )


def resolve_schedule_mode(
    *,
    departure_time: str | None,
    deadline_at: datetime | None,
) -> ScheduleMode:
    if deadline_at is not None:
        return "deadline"
    if departure_time:
        return "departure"
    return "none"


def _everyday_schedule_decision(
    current_price: float | None,
    average: float | None,
) -> tuple[bool, str]:
    if current_price is None or average is None:
        return False, "no_forecast"
    if current_price <= average:
        return True, "normal_price_ok"
    if current_price > average * RED_PRICE_RATIO:
        return False, "smart_wait_expensive"
    return False, "smart_wait_cheaper"


def _balanced_urgency_decision(
    now: datetime,
    *,
    slots: list[tuple[datetime, float]],
    current_price: float | None,
    average: float | None,
    charge_hours: float,
    urgency: float,
) -> tuple[bool, str]:
    if current_price is not None and average is not None and current_price <= average:
        return True, "smart_urgency_balanced"

    hours_needed = max(1, int((charge_hours + urgency * charge_hours) + 0.999))
    # Always leave the most expensive hour of the window out, otherwise a wide
    # urgency window makes every hour qualify and the price rule stops mattering.
    hours_needed = min(hours_needed, max(1, len(slots) - 1))
    cheapest = sorted(slots, key=lambda item: item[1])[:hours_needed]
    cheapest_hours = {_hour_key(ts) for ts, _ in cheapest}
    current_hour = _hour_key(now)
    if current_hour in cheapest_hours:
        return True, "smart_scheduled"
    return False, "smart_wait_cheaper"


def _green_price_decision(
    now: datetime,
    *,
    slots: list[tuple[datetime, float]],
) -> tuple[bool, str]:
    """Charge when the current hour is in the green price tier (matches PriceChart bars)."""
    average = _average_price(slots)
    if average is None:
        return False, "no_forecast"
    current_hour = _hour_key(now)
    hour_price = next((price for ts, price in slots if _hour_key(ts) == current_hour), None)
    if hour_price is None:
        return False, "no_forecast_in_window"
    if _is_green_price(hour_price, average):
        return True, "smart_green_price"
    return False, "smart_wait_cheaper"


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


def price_allows_immediate_grid_charge(
    current_price: float | None,
    price_forecast: tuple[tuple[datetime, float], ...],
    *,
    expensive_threshold: float,
    now: datetime | None = None,
) -> bool:
    """True when grid charging should not be deferred for solar forecast."""
    if current_price is not None and current_price <= expensive_threshold:
        return True
    if current_price is None or not price_forecast:
        return False
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    slots = _hourly_slots(price_forecast, reference - timedelta(hours=1), reference + timedelta(hours=24))
    average = _average_price(slots)
    return average is not None and _is_green_price(current_price, average)
