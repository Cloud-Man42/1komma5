"""Smart charging schedule from 15-minute import (buy) prices."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from energy_core.charging.smart_schedule import GREEN_PRICE_RATIO
from energy_core.price_engine.periods import align_period_start

IMPORT_DEADLINE_RISK_URGENCY = 0.8
IMPORT_BALANCED_URGENCY = 0.4
INTERVAL_HOURS = 0.25


def has_import_prices(
    *,
    current_import_sek_kwh: float | None,
    import_forecast: tuple[tuple[datetime, float], ...],
    min_periods: int = 4,
) -> bool:
    return current_import_sek_kwh is not None and len(import_forecast) >= min_periods


def should_charge_import_price(
    now: datetime,
    *,
    current_period_start: datetime | None = None,
    current_import_sek_kwh: float | None,
    import_forecast: tuple[tuple[datetime, float], ...],
    charge_hours: float = 4.0,
    urgency: float = 0.0,
    min_spread_sek_kwh: float = 0.03,
    lookahead_hours: int = 18,
) -> tuple[bool, str]:
    """Charge during green-tier import prices (<= average * GREEN_PRICE_RATIO)."""
    del charge_hours, min_spread_sek_kwh  # kept for API compatibility

    if current_import_sek_kwh is None or not import_forecast:
        return False, "import_price_missing"

    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    period_start = current_period_start or align_period_start(now)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=UTC)

    clamped_urgency = max(0.0, min(1.0, urgency))
    if clamped_urgency >= IMPORT_DEADLINE_RISK_URGENCY:
        return True, "import_deadline_risk"

    window_end = now + timedelta(hours=lookahead_hours)
    slots = [
        (ts, price)
        for ts, price in import_forecast
        if _as_utc(ts) >= now and _as_utc(ts) <= window_end
    ]
    if not slots:
        return False, "import_no_forecast"

    average = sum(price for _, price in slots) / len(slots)
    green_threshold = average * GREEN_PRICE_RATIO
    period_price = _period_import_price(
        period_start, current_import_sek_kwh, import_forecast
    )

    if clamped_urgency >= IMPORT_BALANCED_URGENCY and period_price <= average:
        return True, "import_balanced_urgency"

    if period_price <= green_threshold:
        return True, "import_cheap_now"

    return False, "import_wait_cheaper"


def _period_import_price(
    period_start: datetime,
    current_import_sek_kwh: float | None,
    import_forecast: tuple[tuple[datetime, float], ...],
) -> float:
    for ts, price in import_forecast:
        if _as_utc(ts) == _as_utc(period_start):
            return price
    return current_import_sek_kwh if current_import_sek_kwh is not None else float("inf")


def import_price_allows_immediate_grid_charge(
    *,
    current_import_sek_kwh: float | None,
    import_forecast: tuple[tuple[datetime, float], ...],
    now: datetime | None = None,
    charge_hours: float = 4.0,
) -> bool:
    now = now or datetime.now(UTC)
    charge, _ = should_charge_import_price(
        now,
        current_import_sek_kwh=current_import_sek_kwh,
        import_forecast=import_forecast,
        charge_hours=charge_hours,
        urgency=0.0,
    )
    return charge


def _as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)
