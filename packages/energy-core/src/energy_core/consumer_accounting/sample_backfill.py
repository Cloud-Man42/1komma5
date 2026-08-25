"""Rebuild spa energy intervals from stored samples."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.consumer_accounting.sampler import ConsumerSampler
from energy_core.consumer_accounting.site_sample import build_site_energy_sample
from energy_core.consumer_accounting.types import DataQuality, SpaEnergySample
from energy_core.db.consumer_repo import ConsumerIntervalRepository, ConsumerSampleRepository
from energy_core.db.models import SiteModel

logger = logging.getLogger(__name__)


def _sample_to_spa_sample(row) -> SpaEnergySample:
    pump_states: dict[str, str] = {}
    if row.pump_states_json:
        try:
            parsed = json.loads(row.pump_states_json)
            if isinstance(parsed, dict):
                pump_states = {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            pump_states = {}
    breakdown: dict[str, float] = {}
    if row.component_breakdown_json:
        try:
            parsed = json.loads(row.component_breakdown_json)
            if isinstance(parsed, dict):
                breakdown = {str(k): float(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, TypeError, ValueError):
            breakdown = {}
    quality = DataQuality.MISSING
    try:
        quality = DataQuality(row.quality or DataQuality.CALCULATED.value)
    except ValueError:
        quality = DataQuality.CALCULATED
    return SpaEnergySample(
        power_w=row.power_w or 0.0,
        energy_delta_wh=row.energy_delta_wh or 0.0,
        heater_active=bool(row.heater_active),
        pump_states=pump_states,
        water_temperature_c=row.water_temperature_c,
        set_temperature_c=row.set_temperature_c,
        source=row.source or "ARCTIC_SPA_REST",
        quality=quality,
        component_breakdown=breakdown,
        recorded_at=row.recorded_at,
    )


class SpaSampleBackfillService:
    def __init__(self) -> None:
        self._sampler = ConsumerSampler()

    async def rebuild_missing_intervals(
        self,
        session: AsyncSession,
        *,
        consumer_id: int,
        site: SiteModel,
        cost_enabled: bool,
        is_sqlite: bool,
        since: datetime | None = None,
        live_overview: dict | None = None,
    ) -> int:
        sample_repo = ConsumerSampleRepository(session)
        interval_repo = ConsumerIntervalRepository(session)
        start = since or datetime(1970, 1, 1, tzinfo=UTC)
        samples = await sample_repo.list_for_period(consumer_id, start=start, end=datetime.now(UTC))
        if len(samples) < 2:
            return 0

        created = 0
        for index in range(1, len(samples)):
            prev_row = samples[index - 1]
            curr_row = samples[index]
            start_time = prev_row.recorded_at
            end_time = curr_row.recorded_at
            if start_time >= end_time:
                continue

            energy_wh = curr_row.energy_delta_wh or 0.0
            if energy_wh <= 0:
                duration_seconds = (end_time - start_time).total_seconds()
                if duration_seconds <= 0:
                    continue
                prev_power = prev_row.power_w or 0.0
                curr_power = curr_row.power_w or 0.0
                avg_power = (prev_power + curr_power) / 2.0
                if avg_power <= 0:
                    continue
                energy_wh = max(0.0, avg_power * (duration_seconds / 3600.0) * 1000.0)
            if energy_wh <= 0:
                continue
            if await interval_repo.has_interval_for_window(consumer_id, start_time=start_time, end_time=end_time):
                continue

            spa_sample = _sample_to_spa_sample(curr_row)
            spa_sample = SpaEnergySample(
                power_w=spa_sample.power_w,
                energy_delta_wh=energy_wh,
                heater_active=spa_sample.heater_active,
                pump_states=spa_sample.pump_states,
                water_temperature_c=spa_sample.water_temperature_c,
                set_temperature_c=spa_sample.set_temperature_c,
                source=spa_sample.source,
                quality=spa_sample.quality,
                component_breakdown=spa_sample.component_breakdown,
                recorded_at=spa_sample.recorded_at,
            )
            duration_hours = max(0.0, (end_time - start_time).total_seconds() / 3600.0)
            site_sample = await build_site_energy_sample(
                session,
                site=site,
                live_overview=live_overview,
                is_sqlite=is_sqlite,
                duration_hours=duration_hours,
                reference_time=end_time,
            )
            await self._sampler.record_interval(
                session,
                consumer_id=consumer_id,
                site=site,
                spa_sample=spa_sample,
                site_sample=site_sample,
                start_time=start_time,
                end_time=end_time,
                is_sqlite=is_sqlite,
                cost_enabled=cost_enabled,
            )
            created += 1

        if created:
            logger.info("Spa sample backfill created %d intervals for consumer_id=%s", created, consumer_id)
        return created

    @staticmethod
    def sample_totals(samples: list) -> dict:
        if not samples:
            return {}
        energy_kwh = sum((row.energy_delta_wh or 0.0) for row in samples) / 1000.0
        powered = [row for row in samples if (row.power_w or 0.0) > 0]
        return {
            "energy_kwh": energy_kwh,
            "max_power_w": max((row.power_w or 0.0 for row in samples), default=0.0),
            "avg_power_w": (sum(row.power_w or 0.0 for row in powered) / len(powered)) if powered else None,
            "samples_with_energy": sum(1 for row in samples if (row.energy_delta_wh or 0.0) > 0),
            "samples_with_power": len(powered),
        }
