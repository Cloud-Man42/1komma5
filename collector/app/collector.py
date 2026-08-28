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
    MarketPriceRepository,
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
from energy_core.normalization import normalize_reading
from energy_core.providers import create_heartbeat_provider_from_db
from energy_core.seed import seed_sites
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.aggregation.service import EnergyAggregationService
from energy_core.snapshots.writer import SnapshotWriter
from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.vehicles.sessions.coordinator import VehicleChargeSessionCoordinator
from energy_core.vehicles.supervisor import VehicleIntegrationSupervisor
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
        self._vehicle_charge_sessions = VehicleChargeSessionCoordinator()
        self._snapshot_writer = SnapshotWriter(self._settings)
        self._energy_aggregation = EnergyAggregationService(is_sqlite=self._settings.is_sqlite)

    async def setup(self) -> None:
        try:
            assert_chargeamps_production_safe(app_env=self._settings.app_env.value)
        except RuntimeError as exc:
            logger.warning("Charge Amps production guard: %s", exc)
        async with self._session_factory() as session:
            await seed_sites(session)
            await self._ev_accounting.setup(session)
            await self._vehicle_charge_sessions.setup(session)
            await session.commit()
        await self._vehicle_supervisor.start()

    async def poll_once(self) -> None:
        reading_count = 0
        async with self._session_factory() as session:
            provider = await create_heartbeat_provider_from_db(session)
            heartbeat_readings = await provider.fetch_readings()

            site_repo = SiteRepository(session)
            reading_repo = EnergyReadingRepository(session, is_sqlite=self._settings.is_sqlite)

            for raw in heartbeat_readings:
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
                await self._collect_market_prices(session, site_repo)
                poll_ctx = SitePollContext(client=await create_heartbeat_client(session))
                await self._run_spa_integration(session, site_repo, poll_ctx)
                await self._run_ev_accounting(session, site_repo, poll_ctx)
                await self._run_vehicle_charge_sessions(session, site_repo, poll_ctx)
                await self._run_energy_balance(session, site_repo, poll_ctx)
                await self._run_solar_forecast(session, site_repo)
                sites = await site_repo.list_all()
                for site in sites:
                    await self._energy_aggregation.rollup_site(session, site)
                await self._snapshot_writer.write_all_sites(session, sites)
                await session.commit()
        except Exception:
            logger.exception("Collector enrichment cycle failed")

        bridge_count = 0
        try:
            async with self._session_factory() as session:
                bridge_count = await self._charging_engine.run_cycle(session)
        except Exception:
            logger.exception("Smart charging cycle failed")

        try:
            async with self._session_factory() as session:
                await self._run_virtual_bridge_cycle(session)
                await self._run_ems_shadow_simulation(session)
        except Exception:
            logger.exception("Virtual Heartbeat bridge cycle failed")

        logger.info("Stored %d readings, smart charging processed %d chargers", reading_count, bridge_count)

    async def _collect_market_prices(self, session, site_repo: SiteRepository) -> None:
        client = await create_heartbeat_client(session)
        if client is None:
            return
        current_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        price_repo = MarketPriceRepository(session, is_sqlite=self._settings.is_sqlite)
        for site in await site_repo.list_all():
            if not site.external_system_id:
                continue
            zone = ZoneInfo(site.timezone)
            now_local = datetime.now(zone)
            day_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end_local = day_start_local + timedelta(days=1)
            from_time = day_start_local.astimezone(UTC)
            to_time = day_end_local.astimezone(UTC)
            if await price_repo.has_price_at(site.id, current_hour):
                continue
            try:
                raw = await client.fetch_market_prices(
                    site.external_system_id,
                    from_iso=from_time.isoformat().replace("+00:00", "Z"),
                    to_iso=to_time.isoformat().replace("+00:00", "Z"),
                    resolution="1h",
                )
                parsed = parse_market_prices(raw)
                await price_repo.upsert_prices(
                    site.id,
                    [
                        (point.timestamp, point.spot_eur_kwh, point.all_in_eur_kwh)
                        for point in parsed.points
                    ],
                )
            except Exception:
                logger.exception("Failed to collect market prices for site %s", site.slug)

    async def _run_spa_integration(self, session, site_repo: SiteRepository, poll_ctx: SitePollContext) -> None:
        if not self._settings.arctic_spa_enabled:
            return
        try:
            live_overviews: dict[str, dict] = {}
            for site in await site_repo.list_all():
                overview = await poll_ctx.live_overview(site)
                if overview is not None:
                    live_overviews[site.slug] = overview
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
        except Exception:
            logger.exception("Arctic Spa integration failed")

    async def _run_ev_accounting(self, session, site_repo: SiteRepository, poll_ctx: SitePollContext) -> None:
        total = 0
        for site in await site_repo.list_all():
            live_overview = await poll_ctx.live_overview(site)
            total += await self._ev_accounting.process_site(
                session,
                site=site,
                live_overview=live_overview,
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("EV accounting processed %d charger ticks", total)

    async def _run_vehicle_charge_sessions(self, session, site_repo: SiteRepository, poll_ctx: SitePollContext) -> None:
        total = 0
        for site in await site_repo.list_all():
            live_overview = await poll_ctx.live_overview(site)
            total += await self._vehicle_charge_sessions.process_site(
                session,
                site=site,
                live_overview=live_overview,
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("Vehicle charge sessions processed %d vehicle ticks", total)

    async def _run_energy_balance(self, session, site_repo: SiteRepository, poll_ctx: SitePollContext) -> None:
        from energy_core.db.ev_charger_repo import EvChargerRepository

        charger_repo = EvChargerRepository(session)
        total = 0
        for site in await site_repo.list_all():
            live_overview = await poll_ctx.live_overview(site)
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
        sites = await site_repo.list_all()
        now = datetime.now(UTC)
        for site in sites:
            try:
                await self._solar_forecast.evaluate_site_observations(session, site, now=now)
            except Exception:
                logger.exception("Solar observation evaluation failed for site %s", site.slug)
        count = await self._solar_forecast.run_due_sites(session, sites)
        if count:
            logger.debug("Solar forecast refreshed for %d sites", count)

    async def run(self) -> None:
        logging.basicConfig(level=self._settings.log_level)
        await self.setup()
        logger.info("Collector started")

        while self._running:
            try:
                async with self._session_factory() as session:
                    hb_repo = HeartbeatSettingsRepository(session)
                    hb_settings = await hb_repo.get_record()
                interval = hb_settings.poll_interval_seconds
                await self.poll_once()
            except Exception:
                logger.exception("Poll cycle failed")
                interval = self._settings.heartbeat_poll_interval
            await asyncio.sleep(interval)

    def stop(self) -> None:
        self._running = False

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
