"""Collector poll loop."""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from energy_core.chargers.chargeamps_config import assert_chargeamps_production_safe
from energy_core.charging.engine import SmartChargingEngine
from energy_core.config import get_settings
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.db.repositories import (
    EnergyReadingRepository,
    SiteRepository,
)
from energy_core.db.session import create_engine, create_session_factory
from energy_core.ev_accounting import EVAccountingCoordinator
from energy_core.consumer_accounting import ConsumerAccountingCoordinator
from energy_core.integrations.arctic_spa.polling import ArcticSpaPollingService
from energy_core.spa_energy.service import SmartSpaEnergyService
from energy_core.energy_balance.coordinator import EnergyBalanceCoordinator
from energy_core.heartbeat.bridge.decision_engine import VirtualChargerDecisionEngine
from energy_core.heartbeat.bridge.constraints import BridgeConstraints
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat_client_factory import create_heartbeat_client
from energy_core.domain import reading_is_actionable
from energy_core.normalization import normalize_reading
from energy_core.providers import create_heartbeat_provider_from_db
from energy_core.seed import seed_sites
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.aggregation.service import EnergyAggregationService
from energy_core.snapshots.writer import SnapshotWriter
from energy_core.vehicles.sessions.coordinator import VehicleChargeSessionCoordinator
from energy_core.vehicles.supervisor import VehicleIntegrationSupervisor
from energy_core.financial.service import FinancialAggregationService
from energy_core.performance.task_metrics import record_collector_task
from app.site_poll_context import SitePollContext

logger = logging.getLogger(__name__)


class Collector:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._engine = create_engine(self._settings)
        self._session_factory = create_session_factory(self._engine)
        self._running = True
        self._charging_engine = SmartChargingEngine()
        self._ev_accounting = EVAccountingCoordinator()
        self._consumer_accounting = ConsumerAccountingCoordinator()
        self._spa_polling = ArcticSpaPollingService()
        self._spa_energy = SmartSpaEnergyService(self._settings)
        self._solar_forecast = SolarForecastCoordinator()
        self._energy_balance = EnergyBalanceCoordinator()
        self._vehicle_supervisor = VehicleIntegrationSupervisor(self._session_factory, self._settings)
        self._vehicle_charge_sessions = VehicleChargeSessionCoordinator(self._settings)
        self._snapshot_writer = SnapshotWriter(self._settings)
        self._energy_aggregation = EnergyAggregationService(is_sqlite=self._settings.is_sqlite)
        self._financial_aggregation = FinancialAggregationService(self._settings)
        self._lane_tasks: list[asyncio.Task] = []

    async def setup(self) -> None:
        assert_chargeamps_production_safe(app_env=self._settings.app_env.value)
        async with self._session_factory() as session:
            await seed_sites(session)
            await self._ev_accounting.setup(session)
            await self._vehicle_charge_sessions.setup(session)
            await session.commit()
        await self._vehicle_supervisor.start()

    async def poll_once(self) -> None:
        """Compatibility wrapper: run all lanes sequentially."""
        await self.run_fast_lane()
        await self.run_medium_lane()
        await self.run_slow_lane()

    async def _run_lane(self, lane: str, task_name: str, coro) -> None:
        import time

        started = time.perf_counter()
        success = True
        error_class: str | None = None
        try:
            await asyncio.wait_for(coro, timeout=float(self._settings.collector_lane_timeout_seconds))
        except Exception as exc:
            success = False
            error_class = type(exc).__name__
            logger.exception("Collector %s lane task %s failed", lane, task_name)
        duration_ms = (time.perf_counter() - started) * 1000.0
        await record_collector_task(
            self._session_factory,
            task_name=task_name,
            lane=lane,
            duration_ms=duration_ms,
            success=success,
            error_class=error_class,
        )

    async def run_fast_lane(self) -> None:
        reading_count = 0
        async with self._session_factory() as session:
            provider = await create_heartbeat_provider_from_db(session)
            heartbeat_readings = await provider.fetch_readings()

            site_repo = SiteRepository(session)
            reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)

            for raw in heartbeat_readings:
                if not reading_is_actionable(raw):
                    logger.warning("Skipping degraded Heartbeat reading for %s", raw.site_slug)
                    continue
                normalized = normalize_reading(raw)
                site = await site_repo.get_by_slug(normalized.site_slug)
                if site is None:
                    logger.warning("Unknown site slug %s, skipping", normalized.site_slug)
                    continue
                await reading_repo.upsert_reading(site.id, normalized)
                reading_count += 1
            await session.commit()

        try:
            async with self._session_factory() as session:
                site_repo = SiteRepository(session)
                await self._run_lane("fast", "market_prices", self._collect_market_prices(session, site_repo))
                poll_ctx = SitePollContext(client=await create_heartbeat_client(session))
                sites = await site_repo.list_all()
                live_overviews = await self._prefetch_live_overviews(session, sites, poll_ctx)
                await self._run_lane(
                    "fast",
                    "energy_balance",
                    self._run_energy_balance(session, site_repo, live_overviews),
                )
                await self._run_lane(
                    "fast",
                    "snapshot_write",
                    self._snapshot_writer.write_all_sites(session, sites),
                )
                await session.commit()
        except Exception:
            logger.exception("Collector fast lane failed")

        bridge_count = 0
        try:
            async with self._session_factory() as session:
                bridge_count = await self._charging_engine.run_cycle(session)
        except Exception:
            logger.exception("Smart charging cycle failed")

        logger.info("Fast lane: %d readings, smart charging processed %d chargers", reading_count, bridge_count)

    async def run_medium_lane(self) -> None:
        try:
            async with self._session_factory() as session:
                site_repo = SiteRepository(session)
                poll_ctx = SitePollContext(client=await create_heartbeat_client(session))
                sites = await site_repo.list_all()
                live_overviews = await self._prefetch_live_overviews(session, sites, poll_ctx)
                await self._run_lane(
                    "medium",
                    "spa_integration",
                    self._run_spa_integration(session, site_repo, live_overviews),
                )
                await self._run_lane(
                    "medium",
                    "ev_accounting",
                    self._run_ev_accounting(session, site_repo, live_overviews),
                )
                await self._run_lane(
                    "medium",
                    "vehicle_charge_sessions",
                    self._run_vehicle_charge_sessions(session, site_repo, live_overviews),
                )
                for site in sites:
                    await self._energy_aggregation.rollup_site(session, site)
                await session.commit()
        except Exception:
            logger.exception("Collector medium lane failed")

        try:
            async with self._session_factory() as session:
                await self._run_lane("medium", "virtual_bridge", self._run_virtual_bridge_cycle(session))
                await self._run_lane("medium", "ems_shadow", self._run_ems_shadow_simulation(session))
        except Exception:
            logger.exception("Collector medium bridge lane failed")

    async def run_slow_lane(self) -> None:
        try:
            async with self._session_factory() as session:
                site_repo = SiteRepository(session)
                sites = await site_repo.list_all()
                await self._run_lane("slow", "solar_forecast", self._run_solar_forecast(session, site_repo))
                await self._run_lane("slow", "forecast_learning", self._run_forecast_learning(session, site_repo))
                await self._run_lane("slow", "energy_control", self._run_energy_control(session, site_repo))
                await self._run_lane(
                    "slow",
                    "chargefinder_health",
                    self._sync_chargefinder_health(session),
                )
                for site in sites:
                    await self._run_lane(
                        "slow",
                        f"financial_rollup:{site.slug}",
                        self._financial_aggregation.rollup_site(session, site),
                    )
                await self._run_lane(
                    "slow",
                    "timescale_retention",
                    self._ensure_timescale_retention(session),
                )
                await self._run_lane(
                    "slow",
                    "timescale_compression",
                    self._ensure_timescale_compression(session),
                )
                await session.commit()
        except Exception:
            logger.exception("Collector slow lane failed")

    async def _collect_market_prices(self, session, site_repo: SiteRepository) -> None:
        from energy_core.integrations.collector_health import record_provider_outcome
        from energy_core.integrations.health import IntegrationHealthRecorder
        from energy_core.price_engine.engine import EmicPriceEngine
        from energy_core.price_engine.observability import log_refresh_result
        import time

        client = await create_heartbeat_client(session)
        if client is None:
            return

        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        engine = EmicPriceEngine(session, is_sqlite=self._settings.is_sqlite)
        for site in await site_repo.list_all():
            if not site.external_system_id:
                continue
            started = time.perf_counter()
            error: str | None = None
            error_class: str | None = None
            count = 0
            try:
                count = await engine.refresh_site(site, client)
            except Exception as exc:
                error = str(exc)
                error_class = type(exc).__name__
                logger.exception("Price engine refresh failed for site %s", site.slug)
            duration_ms = (time.perf_counter() - started) * 1000
            log_refresh_result(site_slug=site.slug, periods_written=count, duration_ms=duration_ms, error=error)
            await record_provider_outcome(
                recorder,
                site.id,
                "price_engine",
                success=error is None,
                error_class=error_class,
                latency_ms=duration_ms,
            )

    async def _run_forecast_learning(self, session, site_repo: SiteRepository) -> None:
        from energy_core.forecast_learning.service import ForecastLearningService

        service = ForecastLearningService(session, is_sqlite=self._settings.is_sqlite)
        total = 0
        for site in await site_repo.list_all():
            try:
                result = await service.sync_site(site.id, timezone=site.timezone)
                total += sum(result.values())
            except Exception:
                logger.exception("Forecast learning sync failed for site %s", site.slug)
        if total:
            logger.debug("Forecast learning synced %d snapshot operations", total)

    async def _ensure_timescale_retention(self, session) -> None:
        from energy_core.db.timescale_retention import ensure_timescale_retention

        result = await ensure_timescale_retention(session, self._settings)
        status = result.get("status")
        if status == "applied":
            logger.info("Timescale retention policies: %s", result.get("policies"))

    async def _ensure_timescale_compression(self, session) -> None:
        from energy_core.db.timescale_retention import ensure_timescale_compression

        result = await ensure_timescale_compression(session, self._settings)
        status = result.get("status")
        if status == "applied":
            logger.info("Timescale compression policies: %s", result.get("policies"))

    async def _run_energy_control(self, session, site_repo: SiteRepository) -> None:
        if not self._settings.energy_control_collector_enabled:
            return
        from energy_core.energy_control.service import EnergyControlService
        from energy_core.integrations.collector_health import record_provider_outcome
        from energy_core.integrations.health import IntegrationHealthRecorder
        from energy_core.price_engine.strategy_service import build_current_strategy_snapshot
        from energy_core.price_engine.types import OptimizationMode

        service = EnergyControlService(session)
        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        count = 0
        for site in await site_repo.list_all():
            if site.optimization_mode == OptimizationMode.MONITOR_ONLY.value:
                continue
            try:
                snapshot = await build_current_strategy_snapshot(
                    session,
                    site,
                    is_sqlite=self._settings.is_sqlite,
                )
                result = await service.sync_from_strategy(site, snapshot)
                await record_provider_outcome(recorder, site.id, "energy_control", success=True)
                if result is not None:
                    count += 1
            except Exception as exc:
                await record_provider_outcome(
                    recorder,
                    site.id,
                    "energy_control",
                    success=False,
                    error_class=type(exc).__name__,
                )
                logger.exception("Energy control sync failed for site %s", site.slug)
        if count:
            logger.debug("Energy control synced %d site actions", count)

    async def _sync_chargefinder_health(self, session) -> None:
        from energy_core.db.chargefinder_integration_status_repo import ChargeFinderIntegrationStatusRepository
        from energy_core.db.vehicle_repo import VehicleProviderRepository
        from energy_core.integrations.charging_stations.chargefinder.provider import ChargeFinderMode
        from energy_core.integrations.charging_stations.chargefinder_health import (
            ChargeFinderHealthStatus,
            ChargeFinderIntegrationHealthService,
        )
        from energy_core.integrations.collector_health import record_provider_outcome
        from energy_core.integrations.health import IntegrationHealthRecorder

        if not self._settings.chargefinder_enabled:
            return

        try:
            mode = ChargeFinderMode(str(self._settings.chargefinder_mode).upper())
        except ValueError:
            mode = ChargeFinderMode.WEB
        if mode == ChargeFinderMode.DISABLED:
            return

        provider_repo = VehicleProviderRepository(session)
        enabled_sites = [site for _row, site in await provider_repo.list_enabled()]
        if not enabled_sites:
            return

        status_repo = ChargeFinderIntegrationStatusRepository(session)
        status = await status_repo.get_or_create()
        health = ChargeFinderIntegrationHealthService().evaluate(
            enabled=self._settings.chargefinder_enabled,
            mode=mode,
            status=status,
        )
        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        success = health.status in {
            ChargeFinderHealthStatus.AVAILABLE,
            ChargeFinderHealthStatus.DEGRADED,
        }
        error_class = None if success else health.status.value
        circuit_breaker_state = None
        if health.status == ChargeFinderHealthStatus.BLOCKED:
            circuit_breaker_state = "open"
        elif health.status == ChargeFinderHealthStatus.DEGRADED:
            circuit_breaker_state = "degraded"

        for site in enabled_sites:
            await record_provider_outcome(
                recorder,
                site.id,
                "chargefinder",
                success=success,
                error_class=error_class,
                latency_ms=float(health.last_latency_ms) if health.last_latency_ms is not None else None,
                circuit_breaker_state=circuit_breaker_state,
            )

    async def _prefetch_live_overviews(self, session, sites, poll_ctx: SitePollContext) -> dict[str, dict]:
        from energy_core.integrations.health import IntegrationHealthRecorder

        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        live_overviews: dict[str, dict] = {}
        for site in sites:
            overview = await poll_ctx.live_overview(site)
            if overview is not None:
                live_overviews[site.slug] = overview
                await recorder.record_success(site.id, "heartbeat")
            else:
                await recorder.record_failure(site.id, "heartbeat", error_class="Unavailable")
        return live_overviews

    async def _run_spa_integration(
        self,
        session,
        site_repo: SiteRepository,
        live_overviews: dict[str, dict],
    ) -> None:
        if not self._settings.arctic_spa_enabled:
            return
        from energy_core.db.consumer_repo import ConsumerRepository
        from energy_core.integrations.collector_health import record_provider_outcome
        from energy_core.integrations.health import IntegrationHealthRecorder

        spa_sites = {
            site.id: site
            for _, _, site in await ConsumerRepository(session).list_enabled_spa_consumers()
        }
        if not spa_sites:
            return

        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        try:
            polled = await self._spa_polling.poll_due_consumers(
                session,
                live_overviews=live_overviews,
                active_cleaning_poll_interval_seconds=self._settings.spa_active_cleaning_poll_interval_seconds,
            )
            for site in await site_repo.list_all():
                await self._consumer_accounting.rebuild_spa_intervals_for_site(
                    session,
                    site=site,
                    live_overview=live_overviews.get(site.slug),
                )
                await self._consumer_accounting.update_aggregates_for_site(session, site=site)
            if polled:
                logger.debug("Arctic Spa polled %d consumers", polled)
            try:
                planned = await self._spa_energy.run_cycle(session)
                if planned:
                    logger.debug("Spa energy planned for %d consumers", planned)
            except Exception:
                logger.exception("Spa smart energy planning failed")
            for site_id in spa_sites:
                await record_provider_outcome(recorder, site_id, "arctic_spa", success=True)
        except Exception as exc:
            for site_id in spa_sites:
                await record_provider_outcome(
                    recorder,
                    site_id,
                    "arctic_spa",
                    success=False,
                    error_class=type(exc).__name__,
                )
            logger.exception("Arctic Spa integration failed")

    async def _run_ev_accounting(
        self,
        session,
        site_repo: SiteRepository,
        live_overviews: dict[str, dict],
    ) -> None:
        total = 0
        for site in await site_repo.list_all():
            total += await self._ev_accounting.process_site(
                session,
                site=site,
                live_overview=live_overviews.get(site.slug),
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("EV accounting processed %d charger ticks", total)

    async def _run_vehicle_charge_sessions(
        self,
        session,
        site_repo: SiteRepository,
        live_overviews: dict[str, dict],
    ) -> None:
        total = 0
        for site in await site_repo.list_all():
            total += await self._vehicle_charge_sessions.process_site(
                session,
                site=site,
                live_overview=live_overviews.get(site.slug),
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("Vehicle charge sessions processed %d vehicle ticks", total)

    async def _run_energy_balance(
        self,
        session,
        site_repo: SiteRepository,
        live_overviews: dict[str, dict],
    ) -> None:
        from energy_core.db.ev_charger_repo import EvChargerRepository

        charger_repo = EvChargerRepository(session)
        total = 0
        for site in await site_repo.list_all():
            live_overview = live_overviews.get(site.slug)
            chargers = await charger_repo.list_for_site(site.id)
            for charger in chargers:
                if not charger.bridge_enabled and not charger.virtual_evse_enabled:
                    continue
                try:
                    await self._energy_balance.run_for_charger(
                        session,
                        site,
                        charger,
                        live_overview=live_overview,
                    )
                    total += 1
                except Exception:
                    logger.exception("Energy balance failed charger_id=%s", charger.id)
        if total:
            logger.debug("Energy balance processed %d chargers", total)

    async def _run_virtual_bridge_cycle(self, session) -> None:
        site_repo = SiteRepository(session)
        charger_repo = EvChargerRepository(session)
        bridge_repo = HeartbeatDiscoveryRepository(session)
        client = await create_heartbeat_client(session)
        if client is None:
            return

        engine = VirtualChargerDecisionEngine(session)
        processed = 0
        for site in await site_repo.list_all():
            if not site.external_system_id:
                continue
            settings = await bridge_repo.get_or_create_bridge_settings(site.id)
            if not settings.virtual_bridge_enabled:
                continue
            mappings = await bridge_repo.list_mappings(site.id)
            enabled = [m for m in mappings if m.enabled]
            if not enabled:
                continue
            try:
                evs = await client.list_evs(site.external_system_id)
                ems = await client.fetch_ems_settings(site.external_system_id)
                now = datetime.now(UTC)
                opts = await client.fetch_optimizations(
                    site.external_system_id,
                    from_iso=(now - timedelta(minutes=30)).isoformat(),
                    to_iso=now.isoformat(),
                )
            except Exception as exc:
                logger.exception("Virtual bridge Heartbeat fetch failed site=%s", site.slug)
                for mapping in enabled:
                    await engine.record_failsafe(
                        site.id,
                        charger_id=mapping.physical_charger_id,
                        heartbeat_ev_id=mapping.heartbeat_ev_id,
                        reason=str(exc),
                    )
                await session.commit()
                continue

            for mapping in enabled:
                ev_profile = next((ev for ev in evs if str(ev.get("id")) == mapping.heartbeat_ev_id), None)
                charger = None
                if mapping.physical_charger_id:
                    charger = await charger_repo.get_by_id(mapping.physical_charger_id)
                max_power = (charger.max_power_w if charger and charger.max_power_w else 11000.0)
                await engine.evaluate(
                    site.id,
                    charger_id=mapping.physical_charger_id,
                    heartbeat_ev_id=mapping.heartbeat_ev_id,
                    ev_profile=ev_profile,
                    ems_settings=ems,
                    optimizations=opts,
                    constraints=BridgeConstraints(
                        heartbeat_requested_power_w=max_power,
                        solar_available_power_w=max_power,
                        smart_charging_allowed_power_w=max_power,
                        load_balancer_allowed_power_w=max_power,
                        halo_hardware_limit_w=max_power,
                        vehicle_limit_w=max_power,
                        site_limit_w=max_power,
                    ),
                    confidence=mapping.confidence_pct,
                )
                processed += 1
        if processed:
            await session.commit()
            logger.debug("Virtual Heartbeat bridge processed %d mappings", processed)

    async def _run_ems_shadow_simulation(self, session) -> None:
        """EMS-only simulation when bridge is in discovery mode without EV mapping."""
        site_repo = SiteRepository(session)
        charger_repo = EvChargerRepository(session)
        bridge_repo = HeartbeatDiscoveryRepository(session)
        client = await create_heartbeat_client(session)
        if client is None:
            return

        engine = VirtualChargerDecisionEngine(session)
        processed = 0
        for site in await site_repo.list_all():
            if not site.external_system_id:
                continue
            settings = await bridge_repo.get_or_create_bridge_settings(site.id)
            if not settings.simulation_mode:
                continue
            enabled_mappings = [m for m in await bridge_repo.list_mappings(site.id) if m.enabled]
            if enabled_mappings:
                continue
            chargers = await charger_repo.list_for_site(site.id)
            if not chargers:
                continue
            try:
                ems = await client.fetch_ems_settings(site.external_system_id)
                now = datetime.now(UTC)
                opts = await client.fetch_optimizations(
                    site.external_system_id,
                    from_iso=(now - timedelta(minutes=30)).isoformat(),
                    to_iso=now.isoformat(),
                )
            except Exception as exc:
                logger.exception("EMS shadow simulation Heartbeat fetch failed site=%s", site.slug)
                await engine.record_failsafe(
                    site.id,
                    charger_id=chargers[0].id,
                    heartbeat_ev_id=None,
                    reason=str(exc),
                )
                await session.commit()
                continue

            charger = chargers[0]
            max_power = charger.max_power_w if charger.max_power_w else 11000.0
            await engine.evaluate(
                site.id,
                charger_id=charger.id,
                heartbeat_ev_id=None,
                ev_profile=None,
                ems_settings=ems,
                optimizations=opts[:1] if opts else [],
                constraints=BridgeConstraints(
                    heartbeat_requested_power_w=max_power,
                    solar_available_power_w=max_power,
                    smart_charging_allowed_power_w=max_power,
                    load_balancer_allowed_power_w=max_power,
                    halo_hardware_limit_w=max_power,
                    vehicle_limit_w=max_power,
                    site_limit_w=max_power,
                ),
                confidence=0.0,
            )
            processed += 1
        if processed:
            await session.commit()
            logger.debug("EMS shadow simulation processed %d sites", processed)

    async def _run_solar_forecast(self, session, site_repo: SiteRepository) -> None:
        from energy_core.integrations.collector_health import record_provider_outcome
        from energy_core.integrations.health import IntegrationHealthRecorder

        sites = await site_repo.list_all()
        now = datetime.now(UTC)
        recorder = IntegrationHealthRecorder(session, is_sqlite=self._settings.is_sqlite)
        for site in sites:
            try:
                await self._solar_forecast.evaluate_site_observations(session, site, now=now)
                await record_provider_outcome(recorder, site.id, "solar_forecast", success=True)
            except Exception as exc:
                await record_provider_outcome(
                    recorder,
                    site.id,
                    "solar_forecast",
                    success=False,
                    error_class=type(exc).__name__,
                )
                logger.exception("Solar observation evaluation failed for site %s", site.slug)
        try:
            count = await self._solar_forecast.run_due_sites(session, sites)
            if count:
                logger.debug("Solar forecast refreshed for %d sites", count)
        except Exception as exc:
            for site in sites:
                await record_provider_outcome(
                    recorder,
                    site.id,
                    "solar_forecast",
                    success=False,
                    error_class=type(exc).__name__,
                )
            logger.exception("Solar forecast refresh failed")

    async def _fast_lane_loop(self) -> None:
        while self._running:
            try:
                async with self._session_factory() as session:
                    hb_repo = HeartbeatSettingsRepository(session)
                    hb_settings = await hb_repo.get_record()
                interval = hb_settings.poll_interval_seconds
                await self.run_fast_lane()
            except Exception:
                logger.exception("Fast lane loop failed")
                interval = self._settings.heartbeat_poll_interval
            await asyncio.sleep(interval)

    async def _medium_lane_loop(self) -> None:
        while self._running:
            try:
                await self.run_medium_lane()
            except Exception:
                logger.exception("Medium lane loop failed")
            await asyncio.sleep(self._settings.collector_medium_lane_interval)

    async def _slow_lane_loop(self) -> None:
        while self._running:
            try:
                await self.run_slow_lane()
            except Exception:
                logger.exception("Slow lane loop failed")
            await asyncio.sleep(self._settings.collector_slow_lane_interval)

    async def run(self) -> None:
        logging.basicConfig(level=self._settings.log_level)
        await self.setup()
        logger.info("Collector started with fast/medium/slow lanes")

        self._lane_tasks = [
            asyncio.create_task(self._fast_lane_loop(), name="collector-fast-lane"),
            asyncio.create_task(self._medium_lane_loop(), name="collector-medium-lane"),
            asyncio.create_task(self._slow_lane_loop(), name="collector-slow-lane"),
        ]
        await asyncio.gather(*self._lane_tasks)

    def stop(self) -> None:
        self._running = False
        for task in self._lane_tasks:
            task.cancel()

    async def shutdown(self) -> None:
        await self._vehicle_supervisor.stop()
        await self._engine.dispose()


async def main() -> None:
    collector = Collector()
    loop = asyncio.get_running_loop()

    def _handle_stop(*_args) -> None:
        collector.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_stop)
        except NotImplementedError:
            pass

    try:
        await collector.run()
    finally:
        await collector.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
