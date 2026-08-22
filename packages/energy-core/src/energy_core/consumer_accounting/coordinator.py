"""Orchestrate spa consumer aggregate updates."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.consumer_accounting.aggregator import merge_interval_into_bucket, period_bounds, quality_percentages
from energy_core.db.consumer_repo import ConsumerAggregateRepository, ConsumerIntervalRepository, ConsumerRepository
from energy_core.db.models import SiteModel

logger = logging.getLogger(__name__)


class ConsumerAccountingCoordinator:
    async def update_aggregates_for_site(self, db: AsyncSession, *, site: SiteModel) -> int:
        repo = ConsumerRepository(db)
        spa_row = await repo.get_spa_for_site(site.id)
        if spa_row is None:
            return 0
        consumer, _config = spa_row
        now = datetime.now(UTC)
        await self._update_aggregates(db, consumer.id, consumer.timezone or site.timezone or "Europe/Stockholm", now)
        return 1

    async def _update_aggregates(
        self,
        db: AsyncSession,
        consumer_id: int,
        timezone: str,
        now: datetime,
    ) -> None:
        from energy_core.consumer_accounting.aggregator import AggregateBucket

        interval_repo = ConsumerIntervalRepository(db)
        agg_repo = ConsumerAggregateRepository(db)
        for granularity in ("hour", "day", "month", "year"):
            start, end = period_bounds(granularity=granularity, reference=now, timezone=timezone)
            intervals = await interval_repo.list_for_period(consumer_id, start=start, end=end)
            if not intervals:
                continue
            bucket = AggregateBucket(granularity=granularity, period_start=start, period_end=end)
            for interval in intervals:
                bucket = merge_interval_into_bucket(bucket, interval)
            q_pct = quality_percentages(bucket.quality_counts or {})
            await agg_repo.upsert(
                consumer_id=consumer_id,
                granularity=granularity,
                period_start=start,
                period_end=end,
                energy_kwh=bucket.energy_kwh,
                solar_direct_kwh=bucket.solar_direct_kwh,
                solar_battery_kwh=bucket.solar_battery_kwh,
                grid_battery_kwh=bucket.grid_battery_kwh,
                grid_direct_kwh=bucket.grid_direct_kwh,
                unknown_kwh=bucket.unknown_kwh,
                actual_cost_sek=bucket.actual_cost_sek,
                reference_cost_sek=bucket.reference_cost_sek or None,
                savings_sek=bucket.savings_sek or None,
                max_power_w=bucket.max_power_w or None,
                avg_power_w=bucket.avg_power_w,
                heater_runtime_seconds=bucket.heater_runtime_seconds,
                pump_runtime_seconds=bucket.pump_runtime_seconds,
                measured_pct=q_pct["measured_pct"],
                calculated_pct=q_pct["calculated_pct"],
                estimated_pct=q_pct["estimated_pct"],
                missing_pct=q_pct["missing_pct"],
            )
