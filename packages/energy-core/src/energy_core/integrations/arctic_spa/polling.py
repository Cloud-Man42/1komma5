"""Background polling for Arctic Spa consumers."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.consumer_accounting.site_sample import build_site_energy_sample
from energy_core.consumer_accounting.sampler import ConsumerSampler
from energy_core.db.consumer_repo import ConsumerRepository, ConsumerSampleRepository
from energy_core.integrations.arctic_spa.client import ArcticSpaApiError
from energy_core.integrations.arctic_spa.config import ArcticSpaConfiguration
from energy_core.integrations.arctic_spa.inferred_meter import InferredArcticSpaMeter
from energy_core.integrations.arctic_spa.service import ArcticSpaService

logger = logging.getLogger(__name__)


class ArcticSpaPollingService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sampler = ConsumerSampler()

    async def poll_due_consumers(
        self,
        session: AsyncSession,
        *,
        live_overviews: dict[str, dict] | None = None,
    ) -> int:
        if self._lock.locked():
            return 0
        async with self._lock:
            repo = ConsumerRepository(session)
            sample_repo = ConsumerSampleRepository(session)
            consumers = await repo.list_enabled_spa_consumers()
            polled = 0
            now = datetime.now(UTC)
            for consumer, config, site in consumers:
                if not config.energy_collection_enabled:
                    continue
                poll_state = await repo.get_poll_state(consumer.id)
                if poll_state and poll_state.backoff_until and poll_state.backoff_until > now:
                    continue
                if poll_state and poll_state.last_success_at:
                    elapsed = (now - poll_state.last_success_at).total_seconds()
                    if elapsed < config.poll_interval_seconds:
                        continue
                try:
                    polled += await self._poll_one(
                        session,
                        repo=repo,
                        sample_repo=sample_repo,
                        consumer=consumer,
                        config=config,
                        site=site,
                        is_sqlite=session.bind.dialect.name == "sqlite" if session.bind else True,
                        now=now,
                        live_overview=(live_overviews or {}).get(site.slug),
                    )
                except Exception:
                    logger.exception("Arctic Spa poll failed consumer_id=%s site=%s", consumer.id, site.slug)
            return polled

    async def _poll_one(
        self,
        session: AsyncSession,
        *,
        repo: ConsumerRepository,
        sample_repo: ConsumerSampleRepository,
        consumer,
        config,
        site,
        is_sqlite: bool,
        now: datetime,
        live_overview: dict | None = None,
    ) -> int:
        cfg = ArcticSpaConfiguration.merge(
            db_enabled=True,
            db_base_url=config.api_base_url,
            db_api_key=config.api_key,
            db_spa_id=config.external_spa_id,
            db_poll_interval=config.poll_interval_seconds,
            db_energy_enabled=config.energy_collection_enabled,
            db_cost_enabled=config.cost_calculation_enabled,
            db_profiles_json=config.power_profiles_json,
        )
        service = ArcticSpaService(cfg)
        prev_status = ConsumerSampler.parse_last_status(config.last_status_json)
        start_time = config.last_status_at or now
        try:
            status = await service.fetch_status()
            await repo.save_status_snapshot(
                consumer.id,
                status_json=status.raw,
                recorded_at=now,
            )
            profiles = cfg.power_profiles
            meter = InferredArcticSpaMeter(profiles=profiles)
            elapsed = 0.0
            if config.last_status_at:
                elapsed = max(0.0, (now - config.last_status_at).total_seconds())
            spa_sample = meter.estimate_sample(
                status,
                prev_status=prev_status,
                elapsed_seconds=elapsed,
                poll_interval_seconds=float(config.poll_interval_seconds),
            )
            await sample_repo.insert_sample(
                consumer_id=consumer.id,
                recorded_at=now,
                power_w=spa_sample.power_w,
                energy_delta_wh=spa_sample.energy_delta_wh,
                water_temperature_c=spa_sample.water_temperature_c,
                set_temperature_c=spa_sample.set_temperature_c,
                heater_active=spa_sample.heater_active,
                pump_states=spa_sample.pump_states,
                filter_status=status.filter_status,
                spa_connected=status.connected,
                source=spa_sample.source,
                quality=spa_sample.quality.value,
                component_breakdown=spa_sample.component_breakdown,
            )
            if spa_sample.energy_delta_kwh > 0 and start_time < now:
                duration_hours = max(0.0, (now - start_time).total_seconds() / 3600.0)
                site_sample = await build_site_energy_sample(
                    session,
                    site=site,
                    live_overview=live_overview,
                    is_sqlite=is_sqlite,
                    duration_hours=duration_hours,
                    reference_time=now,
                )
                await self._sampler.record_interval(
                    session,
                    consumer_id=consumer.id,
                    site=site,
                    spa_sample=spa_sample,
                    site_sample=site_sample,
                    start_time=start_time,
                    end_time=now,
                    is_sqlite=is_sqlite,
                    cost_enabled=config.cost_calculation_enabled,
                )
            await repo.upsert_poll_state(
                consumer.id,
                last_success_at=now,
                consecutive_failures=0,
                last_sample_at=now,
                backoff_until=None,
                polling_active=True,
            )
            return 1
        except ArcticSpaApiError as exc:
            backoff_seconds = min(600, 30 * (2 ** min(await self._failure_count(repo, consumer.id), 5)))
            await repo.upsert_poll_state(
                consumer.id,
                last_error_at=now,
                last_error_message=str(exc)[:500],
                consecutive_failures=(await self._failure_count(repo, consumer.id)) + 1,
                backoff_until=now + timedelta(seconds=backoff_seconds),
                polling_active=False,
            )
            logger.warning("Arctic Spa API error consumer_id=%s: %s", consumer.id, exc)
            return 0

    async def _failure_count(self, repo: ConsumerRepository, consumer_id: int) -> int:
        state = await repo.get_poll_state(consumer_id)
        return state.consecutive_failures if state else 0
