"""Bridge price engine periods into flexible-load horizon inputs."""

from __future__ import annotations

from datetime import UTC, datetime

from energy_core.market_prices.currency import sek_to_eur
from energy_core.price_engine.periods import align_period_start
from energy_core.price_engine.types import PricePeriod


def price_by_period(periods: tuple[PricePeriod, ...]) -> dict[datetime, PricePeriod]:
    """Map aligned UTC period starts to PricePeriod rows."""
    result: dict[datetime, PricePeriod] = {}
    for period in periods:
        start = period.period_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        else:
            start = start.astimezone(UTC)
        aligned = align_period_start(start)
        result[aligned] = period
    return result


def price_by_hour_from_periods(
    periods: tuple[PricePeriod, ...],
) -> dict[datetime, tuple[float | None, float | None]]:
    """Legacy hourly EUR dict for flexible_load (spot, all_in)."""
    hourly: dict[datetime, tuple[float | None, float | None]] = {}
    for period in periods:
        start = period.period_start
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        else:
            start = start.astimezone(UTC)
        hour_key = align_period_start(start, interval_minutes=60)
        spot = (
            sek_to_eur(period.market_price_sek_kwh)
            if period.market_price_sek_kwh is not None
            else None
        )
        all_in = (
            sek_to_eur(period.import_price_sek_kwh)
            if period.import_price_sek_kwh is not None
            else None
        )
        if hour_key not in hourly:
            hourly[hour_key] = (spot, all_in)
    return hourly


def export_value_from_periods(periods: tuple[PricePeriod, ...]) -> float:
    """Best-effort export compensation from the latest period with export price."""
    for period in reversed(periods):
        if period.export_price_sek_kwh is not None:
            return period.export_price_sek_kwh
    return 0.0
