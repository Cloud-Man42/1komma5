"""Multi-site overview orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from energy_core.config import Settings
from energy_core.db.models import FinancialDailyModel, SiteModel
from energy_core.energy_state.models import EnergySiteSnapshot, SystemStatus
from energy_core.energy_state.service import EnergyStateService
from energy_core.multi_site.aggregation import aggregate_sites
from energy_core.multi_site.currency import currency_for_site
from energy_core.multi_site.models import (
    DEFAULT_BATTERY_CAPACITY_KWH,
    MultiSiteOverview,
    SiteOverviewEntry,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo


def multisite_cache_key(slugs: list[str]) -> str:
    return f"emic:multisite:{','.join(sorted(slugs))}:overview"


def _battery_capacity_kwh(site: SiteModel) -> float:
    cap = getattr(site, "battery_usable_capacity_kwh", None)
    return float(cap) if cap is not None else DEFAULT_BATTERY_CAPACITY_KWH


def _health_from_snapshot(snapshot: EnergySiteSnapshot | None, *, error: str | None) -> tuple[str, str | None]:
    if error:
        return "offline", error
    if snapshot is None:
        return "offline", "Ingen data"
    if snapshot.is_stale:
        age = snapshot.data_age_seconds
        detail = f"Data fördröjd {age // 60} min" if age and age >= 60 else "Data fördröjd"
        return "degraded", detail
    if snapshot.system_status in (SystemStatus.OFFLINE, SystemStatus.FAULT):
        return "offline", snapshot.decision_text or "Offline"
    if snapshot.system_status == SystemStatus.PARTIAL:
        return "degraded", "Partiell data"
    return "healthy", None


def _split_grid_power(snapshot: EnergySiteSnapshot) -> tuple[float | None, float | None]:
    if snapshot.grid_import_power_kw is not None or snapshot.grid_export_power_kw is not None:
        return snapshot.grid_import_power_kw, snapshot.grid_export_power_kw
    if snapshot.grid_power_kw is None:
        return None, None
    if snapshot.grid_power_kw >= 0:
        return snapshot.grid_power_kw, 0.0
    return 0.0, abs(snapshot.grid_power_kw)


class MultiSiteAggregationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._energy = EnergyStateService(session, settings)

    async def build_overview(self, sites: list[SiteModel]) -> MultiSiteOverview:
        snapshots = await self._energy.build_snapshots_batch(sites)
        snapshot_by_slug = {s.site_slug: s for s in snapshots}

        financial_tasks = [self._fetch_cost_today(site) for site in sites]
        financials = await asyncio.gather(*financial_tasks)

        entries: list[SiteOverviewEntry] = []
        for site, fin in zip(sites, financials):
            snap = snapshot_by_slug.get(site.slug)
            error = None if snap else "Kunde inte hämta snapshot"
            health, health_detail = _health_from_snapshot(snap, error=error)
            cap = _battery_capacity_kwh(site)
            stored = round(cap * snap.battery_soc_percent / 100, 2) if snap and snap.battery_soc_percent is not None else None
            import_kw, export_kw = _split_grid_power(snap) if snap else (None, None)
            cost, savings = fin

            entries.append(
                SiteOverviewEntry(
                    slug=site.slug,
                    name=site.name,
                    timezone=site.timezone,
                    currency=currency_for_site(site),
                    price_area=site.price_area,
                    available=snap is not None,
                    health=health,
                    health_detail=health_detail,
                    updated_at=snap.updated_at if snap else None,
                    data_age_seconds=snap.data_age_seconds if snap else None,
                    is_stale=snap.is_stale if snap else True,
                    solar_power_kw=snap.solar_power_kw if snap else None,
                    consumption_power_kw=snap.house_power_kw if snap else None,
                    grid_import_power_kw=import_kw,
                    grid_export_power_kw=export_kw,
                    battery_soc_percent=snap.battery_soc_percent if snap else None,
                    battery_power_kw=snap.battery_power_kw if snap else None,
                    battery_capacity_kwh=cap if snap and snap.battery_soc_percent is not None else None,
                    battery_stored_kwh=stored,
                    battery_state=snap.battery_state.value if snap else None,
                    solar_today_kwh=snap.solar_energy_today_kwh if snap else None,
                    consumption_today_kwh=snap.house_energy_today_kwh if snap else None,
                    grid_import_today_kwh=snap.grid_import_today_kwh if snap else None,
                    grid_export_today_kwh=snap.grid_export_today_kwh if snap else None,
                    battery_charged_today_kwh=snap.battery_energy_charged_today_kwh if snap else None,
                    battery_discharged_today_kwh=snap.battery_energy_discharged_today_kwh if snap else None,
                    cost_today=cost,
                    savings_today=savings if savings is not None else (snap.saved_today_sek if snap else None),
                    ev_power_kw=snap.ev_power_kw if snap else None,
                    ev_state=snap.ev_state.value if snap else None,
                    error=error,
                )
            )

        parts = aggregate_sites(entries)
        return MultiSiteOverview(
            sites=tuple(entries),
            aggregate=parts.aggregate,
            health=parts.health,
            data_quality=parts.data_quality,
            freshness=parts.freshness,
            currencies=parts.currencies,
            generated_at=datetime.now(UTC),
        )

    async def _fetch_cost_today(self, site: SiteModel) -> tuple[float | None, float | None]:
        if not self._settings.financial_aggregates_enabled:
            return None, None
        zone = ZoneInfo(site.timezone)
        today_local = datetime.now(zone).date()
        row = await self._session.scalar(
            select(FinancialDailyModel).where(
                FinancialDailyModel.site_id == site.id,
                FinancialDailyModel.day == today_local,
            )
        )
        if row is None:
            return None, None
        cost = round(float(row.grid_import_cost_sek) - float(row.energy_sale_sek or 0), 2)
        savings = round(float(row.solar_savings_sek or 0) + float(row.battery_savings_sek or 0), 2)
        return cost, savings
