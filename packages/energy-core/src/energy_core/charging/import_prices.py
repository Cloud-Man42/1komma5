"""Load price-engine import prices into charging EnergyState."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.energy.state import EnergyState
from energy_core.price_engine.engine import EmicPriceEngine
from energy_core.price_engine.periods import local_today


async def enrich_energy_import_prices(
    session: AsyncSession,
    site: SiteModel,
    energy: EnergyState,
    *,
    is_sqlite: bool,
    now: datetime | None = None,
) -> EnergyState:
    now = now or datetime.now(UTC)
    engine = EmicPriceEngine(session, is_sqlite=is_sqlite)
    current = await engine.get_current(site.id, site.timezone)
    today = local_today(site.timezone, now=now)
    tomorrow = today + timedelta(days=1)
    periods = (
        await engine.get_day(site.id, today, site.timezone)
        + await engine.get_day(site.id, tomorrow, site.timezone)
    )
    forecast = tuple(
        (period.period_start, period.import_price_sek_kwh)
        for period in periods
        if period.import_price_sek_kwh is not None
    )
    return replace(
        energy,
        import_price_sek_kwh=current.import_price_sek_kwh if current else None,
        import_price_forecast=forecast,
    )
