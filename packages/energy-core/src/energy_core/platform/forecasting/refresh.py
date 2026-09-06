"""Unified solar forecast refresh and read resolution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.config import Settings
from energy_core.db.solar_api_snapshot_repo import SolarForecastApiSnapshotRepository
from energy_core.db.solar_forecast_repo import SolarForecastRepository, SolarSiteConfigRepository
from energy_core.platform.forecasting.factory import build_active_forecast_coordinator
from sqlalchemy.ext.asyncio import AsyncSession


def _is_stale(generated_at: datetime | None, *, now: datetime, stale_after: timedelta) -> bool:
    if generated_at is None:
        return True
    generated = generated_at
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=UTC)
    return now - generated > stale_after


async def _refresh_if_stale(
    session: AsyncSession,
    site,
    record,
    settings: Settings,
    *,
    now: datetime,
    stale_after: timedelta,
) -> bool:
    forecast_repo = SolarForecastRepository(session)
    forecast = await forecast_repo.get_latest(site.id)
    if forecast is not None and not _is_stale(forecast.generated_at, now=now, stale_after=stale_after):
        return False

    coordinator = build_active_forecast_coordinator(
        settings,
        solar_intelligence_enabled=bool(record.solar_intelligence_enabled),
    )
    if record.solar_intelligence_enabled:
        refreshed = await coordinator.refresh_site(session, site, now=now)
    else:
        refreshed = await coordinator.refresh_site_now(session, site)
    if refreshed:
        await session.flush()
    return refreshed


async def load_solar_forecast_snapshot(
    session: AsyncSession,
    site_id: int,
    settings: Settings,
) -> dict[str, Any] | None:
    repo = SolarForecastApiSnapshotRepository(session, is_sqlite=settings.is_sqlite)
    stale_after = float(settings.solar_forecast_refresh_minutes * 60)
    return await repo.get_for_site(site_id, stale_after_seconds=stale_after)


async def resolve_forecast_for_read(
    session: AsyncSession,
    site,
    settings: Settings,
):
    """Resolve forecast from DB without synchronous refresh unless explicitly enabled."""
    config_repo = SolarSiteConfigRepository(session)
    record = await config_repo.get(site.id, timezone=site.timezone)
    if record is None or not record.enabled:
        return None, record

    forecast_repo = SolarForecastRepository(session)
    now = datetime.now(UTC)
    stale_after = timedelta(minutes=settings.solar_forecast_refresh_minutes)
    forecast = await forecast_repo.get_latest(site.id)

    if not settings.solar_forecast_sync_refresh_on_read:
        return forecast, record

    if _is_stale(forecast.generated_at if forecast else None, now=now, stale_after=stale_after):
        await _refresh_if_stale(session, site, record, settings, now=now, stale_after=stale_after)
        forecast = await forecast_repo.get_latest(site.id)
    return forecast, record


async def resolve_forecast_with_refresh(
    session: AsyncSession,
    site,
    settings: Settings,
):
    """Refresh stale forecasts when allowed; return latest row (may be None)."""
    config_repo = SolarSiteConfigRepository(session)
    record = await config_repo.get(site.id, timezone=site.timezone)
    if record is None or not record.enabled:
        return None

    forecast_repo = SolarForecastRepository(session)
    now = datetime.now(UTC)
    stale_after = timedelta(minutes=settings.solar_forecast_refresh_minutes)
    forecast = await forecast_repo.get_latest(site.id)

    if record.solar_intelligence_enabled:
        if _is_stale(forecast.generated_at if forecast else None, now=now, stale_after=stale_after):
            if settings.solar_forecast_sync_refresh_on_read:
                await _refresh_if_stale(session, site, record, settings, now=now, stale_after=stale_after)
                forecast = await forecast_repo.get_latest(site.id)
        return forecast

    if forecast is not None:
        return forecast

    if not settings.solar_forecast_sync_refresh_on_read:
        return forecast

    await _refresh_if_stale(session, site, record, settings, now=now, stale_after=stale_after)
    return await forecast_repo.get_latest(site.id)
