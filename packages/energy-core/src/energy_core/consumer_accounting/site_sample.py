"""Build site energy samples for consumer attribution."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.db.repositories import MarketPriceRepository
from energy_core.ev_accounting.models import SiteEnergySample
from energy_core.heartbeat.live_overview import parse_live_overview


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
    price_repo = MarketPriceRepository(session, is_sqlite=is_sqlite)
    hour = when.replace(minute=0, second=0, microsecond=0)
    market_price = await price_repo.get_at(site.id, hour)
    price = (
        market_price.all_in_price_sek_kwh
        if market_price and market_price.all_in_price_sek_kwh
        else site.fallback_purchase_price_sek_kwh
    )

    if not live_overview:
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
