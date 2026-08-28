"""Site live snapshot builder and writer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from energy_core.config import Settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.repositories import EnergyReadingRepository, MarketPriceRepository
from energy_core.db.solar_forecast_repo import SolarForecastRepository, SolarSiteConfigRepository
from energy_core.db.snapshot_repo import SiteLiveSnapshotRepository
from energy_core.solar_forecast.day_metrics import compute_solar_day_metrics
from sqlalchemy.ext.asyncio import AsyncSession

STALE_SECONDS = 480


@dataclass(frozen=True, slots=True)
class SnapshotFreshness:
    level: str
    age_seconds: int | None


def _freshness_from_age(age_seconds: int | None) -> str:
    if age_seconds is None:
        return "DEGRADED"
    if age_seconds <= 120:
        return "LIVE"
    if age_seconds <= STALE_SECONDS:
        return "FRESH"
    if age_seconds <= STALE_SECONDS * 3:
        return "STALE"
    return "DEGRADED"


class SiteSnapshotBuilder:
    """Build site snapshot from DB only — no external provider calls."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def build(self, session: AsyncSession, site) -> dict[str, Any]:
        reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)
        latest = await reading_repo.get_latest_for_site(site.id)

        generated_at = datetime.now(UTC)
        age_seconds: int | None = None
        live: dict[str, Any] | None = None
        if latest is not None:
            recorded_at = latest.recorded_at
            if recorded_at.tzinfo is None:
                recorded_at = recorded_at.replace(tzinfo=UTC)
            age_seconds = max(0, int((generated_at - recorded_at.astimezone(UTC)).total_seconds()))
            live = {
                "solar_production_w": latest.solar_production_w,
                "consumption_w": latest.consumption_w,
                "grid_import_w": latest.grid_import_w,
                "grid_export_w": latest.grid_export_w,
                "battery_soc_pct": latest.battery_soc_pct,
                "battery_power_w": latest.battery_power_w,
            }

        today = await self._build_today(session, site, reading_repo)
        solar = await self._build_solar(session, site)
        economy = await self._build_economy(session, site)
        ev = await self._build_ev(session, site)

        freshness = _freshness_from_age(age_seconds)
        return {
            "site": {"slug": site.slug, "name": site.name, "timezone": site.timezone},
            "generated_at": generated_at.isoformat(),
            "age_seconds": age_seconds,
            "freshness": freshness,
            "source_status": {"heartbeat": "db_only", "forecast": "db_only"},
            "live": live,
            "today": today,
            "solar": solar,
            "economy": economy,
            "ev": ev,
        }

    async def _build_today(self, session, site, reading_repo: EnergyReadingRepository) -> dict[str, Any]:
        zone = ZoneInfo(site.timezone)
        now_local = datetime.now(zone)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(UTC)
        now_utc = now_local.astimezone(UTC)

        from itertools import pairwise

        from energy_core.db.models import EnergyReadingModel
        from sqlalchemy import select

        stmt = (
            select(
                EnergyReadingModel.recorded_at,
                EnergyReadingModel.solar_production_w,
                EnergyReadingModel.consumption_w,
                EnergyReadingModel.grid_import_w,
                EnergyReadingModel.grid_export_w,
            )
            .where(
                EnergyReadingModel.site_id == site.id,
                EnergyReadingModel.recorded_at >= start_utc,
                EnergyReadingModel.recorded_at <= now_utc,
            )
            .order_by(EnergyReadingModel.recorded_at)
        )
        readings = (await session.execute(stmt)).all()
        produced = consumed = imported = exported = 0.0
        for previous, current in pairwise(readings):
            started_at = previous.recorded_at
            ended_at = current.recorded_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=UTC)
            seconds = (ended_at - started_at).total_seconds()
            if seconds <= 0 or seconds > 300:
                continue
            hours = seconds / 3600.0
            produced += max(0.0, float(previous.solar_production_w or 0.0)) * hours / 1000.0
            consumed += max(0.0, float(previous.consumption_w or 0.0)) * hours / 1000.0
            imported += max(0.0, float(previous.grid_import_w or 0.0)) * hours / 1000.0
            exported += max(0.0, float(previous.grid_export_w or 0.0)) * hours / 1000.0

        stats = await reading_repo.list_financial_stats(
            site_id=site.id,
            period="day",
            timezone=site.timezone,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            export_compensation_sek_kwh=site.export_compensation_sek_kwh,
            from_time=start_utc,
            to_time=now_utc + timedelta(seconds=1),
        )
        today_key = now_local.strftime("%Y-%m-%d")
        stat = next((row for row in stats if row.period_start == today_key), None)
        energy_cost = None
        savings = None
        if stat is not None:
            energy_cost = round(stat.grid_import_cost_sek - stat.export_revenue_sek, 2)
            savings = round(stat.solar_savings_sek + stat.battery_savings_sek, 2)

        if len(readings) < 2 and stat is None:
            return {}
        return {
            "produced_kwh": round(produced, 1),
            "consumed_kwh": round(consumed, 1),
            "imported_kwh": round(imported, 1),
            "exported_kwh": round(exported, 1),
            "energy_cost_sek": energy_cost,
            "savings_sek": savings,
        }

    async def _build_solar(self, session, site) -> dict[str, Any]:
        config_repo = SolarSiteConfigRepository(session)
        config = await config_repo.get(site.id, timezone=site.timezone)
        if config is None or not config.enabled:
            return {}
        forecast_repo = SolarForecastRepository(session)
        forecast = await forecast_repo.get_latest(site.id)
        if forecast is None:
            return {}
        day_metrics = compute_solar_day_metrics(forecast, timezone=site.timezone)
        confidence_pct = round(float(forecast.confidence or 0) * 100, 1) if forecast.confidence is not None else None
        return {
            "expected_today_kwh": round(float(day_metrics.expected_today_kwh or 0), 1),
            "remaining_kwh": round(float(day_metrics.remaining_today_kwh or 0), 1),
            "confidence_pct": confidence_pct,
        }

    async def _build_economy(self, session, site) -> dict[str, Any]:
        price_repo = MarketPriceRepository(session, is_sqlite=self._settings.is_sqlite)
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        current = await price_repo.get_at(site.id, now)
        if current is None:
            prices = await price_repo.list_between(
                site.id,
                from_time=now - timedelta(hours=6),
                to_time=now + timedelta(hours=1),
            )
            current = prices[-1] if prices else None
        if current is None:
            return {}
        all_in = current.all_in_price_sek_kwh or current.spot_price_sek_kwh
        tier = "normal"
        return {
            "current_eur_kwh": round(all_in, 4),
            "tier": tier,
        }

    async def _build_ev(self, session, site) -> dict[str, Any]:
        repo = EvChargerRepository(session)
        chargers = await repo.list_for_site(site.id)
        if not chargers:
            return {"available": False}
        charger = next((item for item in chargers if item.bridge_enabled), chargers[0])
        power_w = charger.last_actual_power_w
        return {
            "available": True,
            "charging": (power_w or 0) >= 25,
            "power_w": power_w,
        }


class SnapshotWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._builder = SiteSnapshotBuilder(settings)

    async def write_all_sites(self, session: AsyncSession, sites) -> int:
        repo = SiteLiveSnapshotRepository(session, is_sqlite=self._settings.is_sqlite)
        count = 0
        for site in sites:
            payload = await self._builder.build(session, site)
            await repo.upsert(site.id, payload)
            count += 1
        return count
