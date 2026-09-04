"""Shared strategy snapshot builder for API and collector."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EnergyReadingModel, SiteModel
from energy_core.db.repositories import SiteRepository
from energy_core.price_engine.engine import EmicPriceEngine
from energy_core.price_engine.ev_recommendations import build_ev_recommendations
from energy_core.price_engine.peak_protection import assess_peak_protection
from energy_core.price_engine.periods import local_today
from energy_core.price_engine.strategy import EnergyStrategySnapshot, build_strategy_snapshot


async def build_current_strategy_snapshot(
    session: AsyncSession,
    site: SiteModel,
    *,
    is_sqlite: bool,
) -> EnergyStrategySnapshot:
    engine = EmicPriceEngine(session, is_sqlite=is_sqlite)
    current = await engine.get_current(site.id, site.timezone)
    today = local_today(site.timezone)
    tomorrow = today + timedelta(days=1)
    horizon = (
        await engine.get_day(site.id, today, site.timezone)
        + await engine.get_day(site.id, tomorrow, site.timezone)
    )
    latest_reading = await session.scalar(
        select(EnergyReadingModel)
        .where(EnergyReadingModel.site_id == site.id)
        .order_by(EnergyReadingModel.recorded_at.desc())
        .limit(1)
    )
    battery_soc = latest_reading.battery_soc_pct if latest_reading else None
    mode = await engine.get_status(site.id)
    chargers = await EvChargerRepository(session).list_for_site(site.id)
    peak_hint = assess_peak_protection(
        main_fuse_a=site.main_fuse_a,
        safety_margin_a=site.safety_margin_a or 2.0,
        grid_import_w=latest_reading.grid_import_w if latest_reading else None,
    )
    ev_recs = build_ev_recommendations(
        site=site,
        chargers=tuple(chargers),
        horizon=horizon,
        current_import_sek_kwh=current.import_price_sek_kwh if current else None,
    )
    return build_strategy_snapshot(
        site_slug=site.slug,
        timezone=site.timezone,
        current=current,
        horizon=horizon,
        battery_soc_pct=battery_soc,
        optimization_mode=mode,
        peak_hint=peak_hint,
        ev_recommendations=ev_recs,
    )


async def build_current_strategy_for_slug(
    session: AsyncSession,
    slug: str,
    *,
    is_sqlite: bool,
) -> EnergyStrategySnapshot | None:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        return None
    return await build_current_strategy_snapshot(session, site, is_sqlite=is_sqlite)
