"""Unified solar forecast read and refresh path."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.config import Settings
from energy_core.db.solar_api_snapshot_repo import SolarForecastApiSnapshotRepository
from energy_core.db.solar_forecast_repo import SolarForecastRepository, SolarSiteConfigRepository
from energy_core.platform.forecasting.factory import (
    build_solar_forecast_coordinator,
    build_solar_intelligence_coordinator,
)
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SolarSiteConfigIssue:
    status_code: int
    detail: str


def solar_site_config_issue(record: Any | None) -> SolarSiteConfigIssue | None:
    """Return a config problem for API layers, or None when the site is ready."""
    if record is None or not record.enabled:
        return SolarSiteConfigIssue(
            status_code=404,
            detail=(
                "Solprognos är inte aktiverad. Gå till Inställningar → Anläggningar, "
                "fyll i koordinater och kWp, och aktivera prognosen."
            ),
        )
    if (
        record.latitude is None
        or record.longitude is None
        or record.installed_peak_power_kw is None
        or record.installed_peak_power_kw <= 0
    ):
        return SolarSiteConfigIssue(
            status_code=404,
            detail=(
                "Solprofilen är ofullständig. Ange latitud, longitud och installerad effekt (kWp) "
                "under Inställningar → Anläggningar."
            ),
        )
    return None


async def load_solar_site_config(session: AsyncSession, site) -> tuple[Any | None, SolarSiteConfigIssue | None]:
    repo = SolarSiteConfigRepository(session)
    record = await repo.get(site.id, timezone=site.timezone)
    return record, solar_site_config_issue(record)


def _is_stale(generated_at: datetime | None, *, now: datetime, stale_after: timedelta) -> bool:
    if generated_at is None:
        return True
    generated = generated_at
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=UTC)
    return now - generated > stale_after


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

    if record.solar_intelligence_enabled:
        if _is_stale(forecast.generated_at if forecast else None, now=now, stale_after=stale_after):
            intel = build_solar_intelligence_coordinator(settings)
            if await intel.refresh_site(session, site, now=now):
                await session.flush()
                forecast = await forecast_repo.get_latest(site.id)
        return forecast, record

    if forecast is not None and not _is_stale(forecast.generated_at, now=now, stale_after=stale_after):
        return forecast, record

    coordinator = build_solar_forecast_coordinator(settings)
    refreshed = await coordinator.refresh_site_now(session, site)
    if refreshed:
        await session.flush()
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
                intel = build_solar_intelligence_coordinator(settings)
                if await intel.refresh_site(session, site, now=now):
                    await session.flush()
                    forecast = await forecast_repo.get_latest(site.id)
        return forecast

    if forecast is not None:
        return forecast

    if not settings.solar_forecast_sync_refresh_on_read:
        return forecast

    coordinator = build_solar_forecast_coordinator(settings)
    refreshed = await coordinator.refresh_site_now(session, site)
    if refreshed:
        await session.flush()
        forecast = await forecast_repo.get_latest(site.id)
    return forecast
