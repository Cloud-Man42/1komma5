"""Fast read path for solar forecast API responses."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.config import Settings
from energy_core.db.solar_api_snapshot_repo import SolarForecastApiSnapshotRepository
from energy_core.db.solar_forecast_repo import SolarForecastRepository, SolarSiteConfigRepository
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from sqlalchemy.ext.asyncio import AsyncSession


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

    def _is_stale(f) -> bool:
        if f is None:
            return True
        generated = f.generated_at
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        return now - generated > stale_after

    if not settings.solar_forecast_sync_refresh_on_read:
        return forecast, record

    if record.solar_intelligence_enabled:
        if _is_stale(forecast):
            from energy_core.solar_intelligence.service import SolarIntelligenceCoordinator

            intel = SolarIntelligenceCoordinator(settings)
            if await intel.refresh_site(session, site, now=now):
                await session.flush()
                forecast = await forecast_repo.get_latest(site.id)
        return forecast, record

    if forecast is not None and not _is_stale(forecast):
        return forecast, record

    coordinator = SolarForecastCoordinator(settings)
    refreshed = await coordinator.refresh_site_now(session, site)
    if refreshed:
        await session.flush()
        forecast = await forecast_repo.get_latest(site.id)
    return forecast, record
