"""Financial daily aggregation service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.config import Settings
from energy_core.db.models import EnergyReadingModel, MarketPriceModel
from energy_core.db.repositories import EnergyReadingRepository
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.financial.aggregation import build_price_maps, integrate_financial_daily_accumulators
from energy_core.financial.daily_repo import FinancialDailyRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class FinancialAggregationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def rollup_site(self, session: AsyncSession, site, *, days_back: int = 2) -> int:
        zone = ZoneInfo(site.timezone)
        now_local = datetime.now(zone)
        start_local = (now_local - timedelta(days=days_back - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_utc = start_local.astimezone(UTC)
        end_utc = now_local.astimezone(UTC) + timedelta(days=1)

        reading_stmt = (
            select(
                EnergyReadingModel.recorded_at,
                EnergyReadingModel.solar_production_w,
                EnergyReadingModel.consumption_w,
                EnergyReadingModel.grid_import_w,
                EnergyReadingModel.grid_export_w,
                EnergyReadingModel.battery_power_w,
            )
            .where(
                EnergyReadingModel.site_id == site.id,
                EnergyReadingModel.recorded_at >= start_utc,
                EnergyReadingModel.recorded_at < end_utc,
            )
            .order_by(EnergyReadingModel.recorded_at)
        )
        readings = (await session.execute(reading_stmt)).all()

        price_stmt = (
            select(
                MarketPriceModel.recorded_at,
                MarketPriceModel.spot_price_eur_kwh,
                MarketPriceModel.all_in_price_eur_kwh,
                MarketPriceModel.feed_in_price_eur_kwh,
            )
            .where(
                MarketPriceModel.site_id == site.id,
                MarketPriceModel.recorded_at >= start_utc,
                MarketPriceModel.recorded_at < end_utc,
            )
        )
        price_rows = (await session.execute(price_stmt)).all()
        purchase_prices, spot_prices, feed_in_prices = build_price_maps(price_rows)
        sell_config = sell_price_config_from_site(site)

        daily = integrate_financial_daily_accumulators(
            readings,
            timezone=site.timezone,
            purchase_prices=purchase_prices,
            spot_prices=spot_prices,
            feed_in_prices=feed_in_prices,
            fallback_purchase_price_sek_kwh=site.fallback_purchase_price_sek_kwh,
            config=sell_config,
        )
        repo = FinancialDailyRepository(session, is_sqlite=self._settings.is_sqlite)
        count = 0
        for acc in daily.values():
            await repo.upsert(site.id, acc)
            count += 1
        return count
