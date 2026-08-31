"""Build site energy samples for consumer attribution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.db.repositories import MarketPriceRepository, ReadingRecord
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.heartbeat.live_overview import parse_live_overview

MAX_READING_AGE_SECONDS = 300.0


def nearest_reading_before(
    readings: list[ReadingRecord],
    at_time: datetime,
    *,
    max_age_seconds: float = MAX_READING_AGE_SECONDS,
) -> ReadingRecord | None:
    """Return the latest site reading at or before ``at_time`` within ``max_age_seconds``."""
    if not readings:
        return None
    when = at_time if at_time.tzinfo else at_time.replace(tzinfo=UTC)
    best: ReadingRecord | None = None
    for reading in readings:
        recorded = reading.recorded_at
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=UTC)
        if recorded > when:
            break
        best = reading
    if best is None:
        return None
    recorded = best.recorded_at if best.recorded_at.tzinfo else best.recorded_at.replace(tzinfo=UTC)
    if (when - recorded).total_seconds() > max_age_seconds:
        return None
    return best


def site_energy_sample_from_reading(
    reading: ReadingRecord,
    *,
    duration_hours: float,
    electricity_price_sek_kwh: float,
) -> SiteEnergySample:
    battery_power = reading.battery_power_w or 0.0
    return SiteEnergySample(
        pv_power_w=reading.solar_production_w or 0.0,
        house_consumption_w=reading.consumption_w or 0.0,
        grid_import_w=reading.grid_import_w or 0.0,
        grid_export_w=reading.grid_export_w or 0.0,
        battery_charge_w=max(0.0, battery_power),
        battery_discharge_w=abs(min(0.0, battery_power)),
        ev_power_w=0.0,
        electricity_price_sek_kwh=electricity_price_sek_kwh,
        duration_hours=duration_hours,
    )


async def _price_at(
    session: AsyncSession,
    *,
    site: SiteModel,
    is_sqlite: bool,
    when: datetime,
) -> float:
    from energy_core.market_prices.currency import effective_price_sek_kwh

    price_repo = MarketPriceRepository(session, is_sqlite=is_sqlite)
    hour = when.replace(minute=0, second=0, microsecond=0)
    market_price = await price_repo.get_at(site.id, hour)
    price_sek = effective_price_sek_kwh(market_price)
    if price_sek is not None:
        return price_sek
    return site.fallback_purchase_price_sek_kwh


async def build_site_energy_sample_for_interval(
    session: AsyncSession,
    *,
    site: SiteModel,
    is_sqlite: bool,
    duration_hours: float,
    at_time: datetime,
    live_overview: dict | None = None,
    site_readings: list[ReadingRecord] | None = None,
) -> SiteEnergySample:
    """Prefer Heartbeat readings at interval time; fall back to live overview or zeros."""
    when = at_time if at_time.tzinfo else at_time.replace(tzinfo=UTC)
    price = await _price_at(session, site=site, is_sqlite=is_sqlite, when=when)

    reading = nearest_reading_before(site_readings or [], when)
    if reading is not None:
        return site_energy_sample_from_reading(
            reading,
            duration_hours=duration_hours,
            electricity_price_sek_kwh=price,
        )

    if live_overview:
        parsed = parse_live_overview(live_overview)
        return SiteEnergySample(
            pv_power_w=parsed.get("pv_power_w") or 0.0,
            house_consumption_w=parsed.get("home_consumption_w") or 0.0,
            grid_import_w=parsed.get("grid_import_w") or 0.0,
            grid_export_w=parsed.get("grid_export_w") or 0.0,
            battery_charge_w=parsed.get("battery_charge_power_w") or 0.0,
            battery_discharge_w=parsed.get("battery_discharge_power_w") or 0.0,
            ev_power_w=0.0,
            electricity_price_sek_kwh=price,
            duration_hours=duration_hours,
        )

    return SiteEnergySample(
        pv_power_w=0.0,
        house_consumption_w=0.0,
        grid_import_w=0.0,
        grid_export_w=0.0,
        battery_charge_w=0.0,
        battery_discharge_w=0.0,
        ev_power_w=0.0,
        electricity_price_sek_kwh=price,
        duration_hours=duration_hours,
    )


async def build_site_energy_sample(
    session: AsyncSession,
    *,
    site: SiteModel,
    live_overview: dict | None,
    is_sqlite: bool,
    duration_hours: float,
    reference_time: datetime | None = None,
) -> SiteEnergySample:
    """Create a site sample from Heartbeat live overview, or fallback when unavailable."""
    when = reference_time or datetime.now(UTC)
    return await build_site_energy_sample_for_interval(
        session,
        site=site,
        is_sqlite=is_sqlite,
        duration_hours=duration_hours,
        at_time=when,
        live_overview=live_overview,
    )
