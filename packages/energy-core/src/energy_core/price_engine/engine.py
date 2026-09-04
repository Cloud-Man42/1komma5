"""EmicPriceEngine — central price snapshot orchestrator."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.price_period_repo import PriceEngineStateRepository, PricePeriodRepository
from energy_core.db.repositories import MarketPriceRepository, SiteRepository
from energy_core.export_revenue.site_config import sell_price_config_from_site
from energy_core.price_engine.normalizer import merge_period_layers, normalize_to_periods
from energy_core.price_engine.periods import (
    current_period_start,
    enumerate_local_day_periods,
    local_day_bounds,
    local_today,
)
from energy_core.price_engine.providers.registry import build_heartbeat_providers
from energy_core.price_engine.site_config import config_from_site
from energy_core.price_engine.types import Currency, OptimizationMode, PricePeriod, PriceQuality

logger = logging.getLogger(__name__)

RETENTION_DAYS = 90


class EmicPriceEngine:
    def __init__(
        self,
        session: AsyncSession,
        *,
        is_sqlite: bool = False,
    ) -> None:
        self._session = session
        self._period_repo = PricePeriodRepository(session, is_sqlite=is_sqlite)
        self._state_repo = PriceEngineStateRepository(session)
        self._site_repo = SiteRepository(session)
        self._legacy_repo = MarketPriceRepository(session, is_sqlite=is_sqlite)
        self._is_sqlite = is_sqlite

    async def refresh_site(self, site, client) -> int:
        """Fetch providers, normalize, persist 15-min periods for today + tomorrow."""
        cfg = config_from_site(site)
        if not cfg.external_system_id:
            return 0

        providers = build_heartbeat_providers(client, site)
        tz = cfg.timezone
        today = local_today(tz)
        tomorrow = today + timedelta(days=1)

        total = 0
        now = datetime.now(UTC)
        last_error: str | None = None

        for day in (today, tomorrow):
            try:
                count = await self._refresh_day(site, cfg, providers, day, client)
                total += count
            except Exception as exc:
                last_error = str(exc)
                logger.exception("Price engine refresh failed for site %s day %s", site.slug, day)

        await self._sync_legacy_hourly(site, client)

        newest = await self._period_repo.list_range(
            site.id,
            start=now - timedelta(hours=1),
            end=now + timedelta(days=2),
        )
        data_age = None
        if newest:
            latest = max(p.period_start for p in newest)
            data_age = max(0, int((now - latest).total_seconds()))

        expected_today = len(enumerate_local_day_periods(today, tz))
        stored_today = len(await self._period_repo.list_range(
            site.id,
            start=local_day_bounds(today, tz)[0],
            end=local_day_bounds(today, tz)[1],
        ))
        missing = max(0, expected_today - stored_today)

        await self._state_repo.upsert(
            site_id=site.id,
            last_market_refresh_at=now,
            last_import_refresh_at=now,
            last_export_refresh_at=now,
            last_error=last_error,
            missing_periods_count=missing,
            data_age_seconds=data_age,
            optimization_mode=cfg.optimization_mode,
        )

        cutoff = now - timedelta(days=RETENTION_DAYS)
        await self._period_repo.delete_older_than(site.id, cutoff)
        return total

    async def _refresh_day(self, site, cfg, providers, day: date, client) -> int:
        day_start, day_end = local_day_bounds(day, cfg.timezone)
        from_iso = day_start.isoformat().replace("+00:00", "Z")
        to_iso = day_end.isoformat().replace("+00:00", "Z")

        resolution = "15m"
        try:
            market_raw = await providers.market.fetch(
                system_id=cfg.external_system_id,
                from_iso=from_iso,
                to_iso=to_iso,
                resolution=resolution,
            )
            if not market_raw:
                resolution = "1h"
                market_raw = await providers.market.fetch(
                    system_id=cfg.external_system_id,
                    from_iso=from_iso,
                    to_iso=to_iso,
                    resolution=resolution,
                )
        except Exception:
            resolution = "1h"
            market_raw = await providers.market.fetch(
                system_id=cfg.external_system_id,
                from_iso=from_iso,
                to_iso=to_iso,
                resolution=resolution,
            )

        import_raw = await providers.import_prices.fetch(
            system_id=cfg.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution=resolution,
        )
        export_raw = await providers.export.fetch(
            system_id=cfg.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            sell_config=providers.sell_config,
            resolution=resolution,
        )

        market_rows = normalize_to_periods(
            market_raw,
            site_id=site.id,
            price_area=cfg.price_area,
            currency=Currency.SEK,
        )
        import_rows = normalize_to_periods(
            import_raw,
            site_id=site.id,
            price_area=cfg.price_area,
            currency=Currency.SEK,
        )
        export_rows = normalize_to_periods(
            export_raw,
            site_id=site.id,
            price_area=cfg.price_area,
            currency=Currency.SEK,
        )
        merged = merge_period_layers(market_rows, import_rows, export_rows)
        return await self._period_repo.upsert_periods(merged)

    async def _sync_legacy_hourly(self, site, client) -> None:
        """Keep market_prices table updated for financial stats during transition."""
        cfg = config_from_site(site)
        if not cfg.external_system_id:
            return
        tz = cfg.timezone
        today = local_today(tz)
        day_start, day_end = local_day_bounds(today, tz)
        from_iso = day_start.isoformat().replace("+00:00", "Z")
        to_iso = day_end.isoformat().replace("+00:00", "Z")

        providers = build_heartbeat_providers(client, site)
        market_raw = await providers.market.fetch(
            system_id=cfg.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution="1h",
        )
        import_raw = await providers.import_prices.fetch(
            system_id=cfg.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            resolution="1h",
        )
        export_raw = await providers.export.fetch(
            system_id=cfg.external_system_id,
            from_iso=from_iso,
            to_iso=to_iso,
            sell_config=providers.sell_config,
            resolution="1h",
        )

        by_ts: dict[datetime, tuple[float, float | None, float | None]] = {}
        for point in market_raw:
            ts = point.timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            spot = point.market_price_eur_kwh
            by_ts.setdefault(ts, (spot or 0.0, None, None))
        for point in import_raw:
            ts = point.timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            spot, _, feed = by_ts.get(ts, (0.0, None, None))
            by_ts[ts] = (spot, point.import_price_eur_kwh, feed)
        for point in export_raw:
            ts = point.timestamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            spot, all_in, _ = by_ts.get(ts, (0.0, None, None))
            by_ts[ts] = (spot, all_in, point.export_price_eur_kwh)

        if by_ts:
            await self._legacy_repo.upsert_prices(
                site.id,
                [(ts, spot, all_in, feed) for ts, (spot, all_in, feed) in sorted(by_ts.items())],
            )

    async def get_current(self, site_id: int, timezone: str) -> PricePeriod | None:
        start = current_period_start(timezone=timezone)
        return await self._period_repo.get_at(site_id, start)

    async def get_day(self, site_id: int, day: date, timezone: str) -> tuple[PricePeriod, ...]:
        day_start, day_end = local_day_bounds(day, timezone)
        return await self._period_repo.list_range(site_id, start=day_start, end=day_end)

    async def get_range(
        self,
        site_id: int,
        *,
        start: datetime,
        end: datetime,
    ) -> tuple[PricePeriod, ...]:
        if (end - start) > timedelta(days=7):
            end = start + timedelta(days=7)
        return await self._period_repo.list_range(site_id, start=start, end=end)

    async def get_status(self, site_id: int) -> OptimizationMode:
        state = await self._state_repo.get(site_id)
        if state is None:
            return OptimizationMode.MONITOR_ONLY
        return state.optimization_mode
