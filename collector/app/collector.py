"""Collector poll loop."""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import UTC, datetime, timedelta

from energy_core.chargers.chargeamps_config import assert_chargeamps_production_safe
from energy_core.charging.engine import SmartChargingEngine
from energy_core.config import get_settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_settings_repo import HeartbeatSettingsRepository
from energy_core.heartbeat.ev_sync import HeartbeatEvSyncService
from energy_core.db.repositories import (
    EnergyReadingRepository,
    MarketPriceRepository,
    SiteRepository,
)
from energy_core.db.session import create_engine, create_session_factory
from energy_core.ev_accounting import EVAccountingCoordinator
from energy_core.consumer_accounting import ConsumerAccountingCoordinator
from energy_core.integrations.arctic_spa.polling import ArcticSpaPollingService
from energy_core.energy_balance.coordinator import EnergyBalanceCoordinator
from energy_core.heartbeat.market_prices import parse_market_prices
from energy_core.heartbeat_client_factory import create_heartbeat_client
from energy_core.normalization import normalize_reading
from energy_core.providers import create_heartbeat_provider_from_db
from energy_core.seed import seed_sites
from energy_core.solar_forecast.coordinator import SolarForecastCoordinator
from energy_core.vehicles.supervisor import VehicleIntegrationSupervisor
from energy_core.vehicles.sessions import VehicleChargeSessionCoordinator

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
        self._solar_forecast = SolarForecastCoordinator()
        self._energy_balance = EnergyBalanceCoordinator()
        self._vehicle_supervisor = VehicleIntegrationSupervisor(self._session_factory, self._settings)
        self._vehicle_charge_sessions = VehicleChargeSessionCoordinator()

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
            await self._collect_market_prices(session, site_repo)
            await self._run_spa_integration(session, site_repo)
            await self._run_ev_accounting(session, site_repo)
            await self._run_vehicle_charge_sessions(session, site_repo)
            await self._run_energy_balance(session, site_repo)
            await self._run_solar_forecast(session, site_repo)
            await self._run_heartbeat_ev_sync_fallback(session)
            await session.commit()

        bridge_count = 0
        try:
            async with self._session_factory() as session:
                bridge_count = await self._charging_engine.run_cycle(session)
        except Exception:
            logger.exception("Smart charging cycle failed")

        logger.info("Stored %d readings, smart charging processed %d chargers", reading_count, bridge_count)

    async def _collect_market_prices(self, session, site_repo: SiteRepository) -> None:
        client = await create_heartbeat_client(session)
        if client is None:
            return
        current_hour = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        price_repo = MarketPriceRepository(session, is_sqlite=self._settings.is_sqlite)
        for site in await site_repo.list_all():
            if not site.external_system_id or await price_repo.has_price_at(site.id, current_hour):
                continue
            try:
                raw = await client.fetch_market_prices(
                    site.external_system_id,
                    from_iso=current_hour.isoformat().replace("+00:00", "Z"),
                    to_iso=(current_hour + timedelta(hours=24)).isoformat().replace("+00:00", "Z"),
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

    async def _run_spa_integration(self, session, site_repo: SiteRepository) -> None:
        if not self._settings.arctic_spa_enabled:
            return
        try:
            polled = await self._spa_polling.poll_due_consumers(session)
            for site in await site_repo.list_all():
                await self._consumer_accounting.update_aggregates_for_site(session, site=site)
            if polled:
                logger.debug("Arctic Spa polled %d consumers", polled)
        except Exception:
            logger.exception("Arctic Spa integration failed")

    async def _run_ev_accounting(self, session, site_repo: SiteRepository) -> None:
        client = await create_heartbeat_client(session)
        total = 0
        for site in await site_repo.list_all():
            live_overview = None
            if client is not None and site.external_system_id:
                try:
                    live_overview = await client.fetch_live_overview(site.external_system_id)
                except Exception:
                    logger.exception("Failed to fetch live overview for EV accounting site %s", site.slug)
            total += await self._ev_accounting.process_site(
                session,
                site=site,
                live_overview=live_overview,
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("EV accounting processed %d charger ticks", total)

    async def _run_vehicle_charge_sessions(self, session, site_repo: SiteRepository) -> None:
        client = await create_heartbeat_client(session)
        total = 0
        for site in await site_repo.list_all():
            live_overview = None
            if client is not None and site.external_system_id:
                try:
                    live_overview = await client.fetch_live_overview(site.external_system_id)
                except Exception:
                    logger.exception("Failed to fetch live overview for vehicle sessions site %s", site.slug)
            total += await self._vehicle_charge_sessions.process_site(
                session,
                site=site,
                live_overview=live_overview,
                is_sqlite=self._settings.is_sqlite,
            )
        if total:
            logger.debug("Vehicle charge sessions processed %d vehicle ticks", total)

    async def _run_energy_balance(self, session, site_repo: SiteRepository) -> None:
        from energy_core.db.ev_charger_repo import EvChargerRepository

        client = await create_heartbeat_client(session)
        charger_repo = EvChargerRepository(session)
        total = 0
        for site in await site_repo.list_all():
            live_overview = None
            if client is not None and site.external_system_id:
                try:
                    live_overview = await client.fetch_live_overview(site.external_system_id)
                except Exception:
                    logger.exception("Failed to fetch live overview for energy balance site %s", site.slug)
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

    async def _run_solar_forecast(self, session, site_repo: SiteRepository) -> None:
        sites = await site_repo.list_all()
        count = await self._solar_forecast.run_due_sites(session, sites)
        if count:
            logger.debug("Solar forecast refreshed for %d sites", count)

    async def _run_heartbeat_ev_sync_fallback(self, session) -> None:
        hb_repo = HeartbeatSettingsRepository(session)
        if not await hb_repo.is_write_enabled():
            return
        charger_repo = EvChargerRepository(session)
        sync_service = HeartbeatEvSyncService(session)
        now = datetime.now(UTC)
        synced = 0
        for charger, site in await charger_repo.list_heartbeat_sync_enabled_with_sites():
            if charger.last_bridge_run_at is not None:
                elapsed = (now - charger.last_bridge_run_at).total_seconds()
                if elapsed < 60:
                    continue
            try:
                await sync_service.sync_charger(charger, site)
                synced += 1
            except Exception:
                logger.exception("Heartbeat EV sync fallback failed charger_id=%s", charger.id)
        if synced:
            logger.debug("Heartbeat EV sync fallback processed %d chargers", synced)

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
