"""Shared spa read/compute helpers for API and display layers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.auth.principal import Principal
from energy_core.config import Settings
from energy_core.consumer_accounting.aggregator import period_bounds
from energy_core.db.consumer_repo import ConsumerIntervalRepository, ConsumerRepository, ConsumerSampleRepository
from energy_core.db.repositories import SiteRepository


async def get_spa_context(
    session: AsyncSession,
    slug: str,
    *,
    principal: Principal | None = None,
    settings: Settings | None = None,
    permission: str = "spa.read",
):
    if principal is not None and settings is not None:
        from app.site_access import require_site_with_permission

        site = await require_site_with_permission(session, principal, settings, slug, permission)
    else:
        site_repo = SiteRepository(session)
        site = await site_repo.get_by_slug(slug)
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    repo = ConsumerRepository(session)
    row = await repo.get_spa_by_site_slug(slug)
    if row is None:
        consumer, config = await repo.get_or_create_spa(site)
        await session.flush()
        return site, consumer, config
    consumer, config, _site = row
    return site, consumer, config


def normalize_spa_period(period: str) -> str:
    if period == "day":
        return "24h"
    return period


def spa_period_range(period: str, timezone: str) -> tuple[datetime, datetime, str]:
    period = normalize_spa_period(period)
    now = datetime.now(UTC)
    if period == "24h":
        return now - timedelta(hours=24), now, "hour"
    if period == "today":
        start, end = period_bounds(granularity="day", reference=now, timezone=timezone)
        return start, end, "day"
    if period == "week":
        start = now - timedelta(days=7)
        return start, now, "day"
    if period == "month":
        start, end = period_bounds(granularity="month", reference=now, timezone=timezone)
        return start, end, "month"
    if period == "year":
        start, end = period_bounds(granularity="year", reference=now, timezone=timezone)
        return start, end, "year"
    if period == "rolling12":
        return now - timedelta(days=365), now, "month"
    if period == "total":
        return datetime(1970, 1, 1, tzinfo=UTC), now, "day"
    raise HTTPException(status_code=422, detail="Invalid period")


async def spa_period_energy_totals(
    session: AsyncSession,
    consumer_id: int,
    *,
    start: datetime,
    end: datetime,
    fallback_price_sek_kwh: float,
    site,
) -> dict:
    interval_repo = ConsumerIntervalRepository(session)
    totals = await interval_repo.sum_for_period(consumer_id, start=start, end=end)
    if totals:
        return totals

    sample_repo = ConsumerSampleRepository(session)
    sample_totals = await sample_repo.sum_for_period(consumer_id, start=start, end=end)
    energy = sample_totals.get("energy_kwh", 0.0) or 0.0
    if energy <= 0:
        return {}
    return {
        "energy_kwh": energy,
        "solar_direct_kwh": 0.0,
        "solar_battery_kwh": 0.0,
        "grid_battery_kwh": 0.0,
        "grid_direct_kwh": energy,
        "unknown_kwh": 0.0,
        "actual_cost_sek": energy * fallback_price_sek_kwh,
        "reference_cost_sek": energy * fallback_price_sek_kwh,
        "savings_sek": 0.0,
        "heater_runtime_seconds": 0.0,
        "pump_runtime_seconds": 0.0,
        "max_power_w": sample_totals.get("max_power_w"),
    }
