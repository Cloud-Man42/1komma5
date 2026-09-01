"""Background supervisor for vehicle integrations in the collector."""

from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime

from energy_core.config import Settings
from energy_core.db.attribute_observation_repo import VehicleAttributeObservationRepository
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.charging_intelligence.location import HaloCorrelationHint, is_away_charging
from energy_core.secrets import SecretBox, SecretBoxError
from energy_core.vehicles.abstractions.models import VehicleConnectionState, VehicleState
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle
from energy_core.vehicles.polling import AdaptivePollingPlanner
from energy_core.vehicles.mercedes.provider import MercedesProvider
from energy_core.vehicles.mock.provider import MockVehicleProvider, MockVehicleScenario

REST_REFRESH_SECONDS = 300

logger = logging.getLogger(__name__)


@dataclass
class _SiteRuntime:
    site_id: int
    site_slug: str
    provider: object
    task: asyncio.Task | None = None


@dataclass(frozen=True, slots=True)
class _PollingContext:
    is_charging: bool | None = None
    is_plugged_in: bool | None = None
    charging_power_kw: float | None = None
    last_vehicle_update: datetime | None = None
    soc_updated_at: datetime | None = None
    missing_gps: bool = True
    away_from_home: bool = False


def _halo_charger_active(charger) -> bool | None:
    if charger is None:
        return None
    if charger.last_vehicle_connected is True:
        return True
    if charger.last_actual_power_w is not None and charger.last_actual_power_w > 300:
        return True
    if charger.last_vehicle_connected is False:
        if charger.last_actual_power_w is None or charger.last_actual_power_w <= 300:
            return False
    return None


def _build_polling_context(db_latest, latest_state, correlation, charger) -> _PollingContext:
    is_charging = db_latest.is_charging if db_latest is not None else (latest_state.is_charging if latest_state else None)
    is_plugged_in = (
        db_latest.is_plugged_in if db_latest is not None else (latest_state.is_plugged_in if latest_state else None)
    )
    charging_power_kw = (
        db_latest.charging_power_kw
        if db_latest is not None
        else (latest_state.charging_power_kw if latest_state else None)
    )
    last_vehicle_update = (
        db_latest.last_vehicle_update
        if db_latest is not None
        else (latest_state.last_vehicle_update if latest_state else None)
    )
    soc_updated_at = getattr(db_latest, "soc_updated_at", None) if db_latest is not None else None
    latitude = db_latest.latitude if db_latest is not None else (latest_state.latitude if latest_state else None)
    longitude = db_latest.longitude if db_latest is not None else (latest_state.longitude if latest_state else None)
    halo = (
        HaloCorrelationHint(status=correlation.status, plugged_agreement=correlation.plugged_agreement)
        if correlation is not None
        else None
    )
    return _PollingContext(
        is_charging=is_charging,
        is_plugged_in=is_plugged_in,
        charging_power_kw=charging_power_kw,
        last_vehicle_update=last_vehicle_update,
        soc_updated_at=soc_updated_at,
        missing_gps=latitude is None or longitude is None,
        away_from_home=is_away_charging(
            halo=halo,
            mercedes_plugged=is_plugged_in,
            mercedes_charging=is_charging,
            mercedes_power_kw=charging_power_kw,
            halo_charger_active=_halo_charger_active(charger),
        ),
    )


class VehicleIntegrationSupervisor:
    def __init__(self, session_factory, settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._secret_box = SecretBox.from_settings()
        self._runtimes: dict[int, _SiteRuntime] = {}
        self._supervisor_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._supervisor_task is not None:
            return
        self._running = True
        self._supervisor_task = asyncio.create_task(self._supervisor_loop())
        logger.info("Vehicle integration supervisor started")

    async def stop(self) -> None:
        self._running = False
        if self._supervisor_task is not None:
            self._supervisor_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._supervisor_task
            self._supervisor_task = None
        for runtime in list(self._runtimes.values()):
            await self._stop_site(runtime)
        self._runtimes.clear()
        logger.info("Vehicle integration supervisor stopped")

    async def _supervisor_loop(self) -> None:
        while self._running:
            try:
                async with self._session_factory() as session:
                    provider_repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                    enabled = await provider_repo.list_enabled()
                    enabled_ids = {row.site_id for row, _site in enabled}
                    for row, site in enabled:
                        runtime = self._runtimes.get(row.site_id)
                        if runtime is None:
                            runtime = _SiteRuntime(
                                site_id=site.id,
                                site_slug=site.slug,
                                provider=await self._build_provider(row, provider_repo),
                            )
                            runtime.task = asyncio.create_task(self._run_site(runtime, row.id))
                            self._runtimes[row.site_id] = runtime
                        elif runtime.task is None or runtime.task.done():
                            runtime.provider = await self._build_provider(row, provider_repo)
                            runtime.task = asyncio.create_task(self._run_site(runtime, row.id))
                    for site_id in list(self._runtimes):
                        if site_id not in enabled_ids:
                            await self._stop_site(self._runtimes.pop(site_id))
                    await session.commit()
            except Exception:
                logger.exception("Vehicle supervisor refresh failed")
            await asyncio.sleep(15)

    async def _build_provider(self, row, provider_repo: VehicleProviderRepository):
        if self._settings.app_env.value == "test":
            return MockVehicleProvider(scenario=MockVehicleScenario.CONNECTED_IDLE)
        try:
            token_bundle = provider_repo.load_token_bundle(row)
        except SecretBoxError:
            token_bundle = None
        device_guid = row.device_guid or str(uuid.uuid4())
        provider = MercedesProvider(region=row.region, device_guid=device_guid, token_bundle=token_bundle)

        async def persist(bundle: MercedesTokenBundle) -> None:
            async with self._session_factory() as session:
                repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                db_row = await repo.get_for_site(row.site_id)
                if db_row is not None:
                    await repo.persist_token_bundle(db_row, bundle)
                    await repo.update_runtime_status(db_row, last_token_refresh_at=datetime.now(UTC))
                    await session.commit()

        async def reload() -> MercedesTokenBundle | None:
            async with self._session_factory() as session:
                repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                db_row = await repo.get_for_site(row.site_id)
                if db_row is None:
                    return None
                return await repo.load_token_bundle_for_update(db_row)

        provider._token_store._persist = persist  # noqa: SLF001
        provider._token_store._reload = reload  # noqa: SLF001
        return provider

    async def _run_site(self, runtime: _SiteRuntime, connection_id: int) -> None:
        site_id = runtime.site_id
        try:
            provider = runtime.provider
            if isinstance(provider, MercedesProvider):
                username = ""
                password = ""
                async with self._session_factory() as session:
                    repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                    row = await repo.get_for_site(runtime.site_id)
                    if row is not None:
                        username = row.username or ""
                        if provider._token_store._token is None:  # noqa: SLF001
                            if not row.encrypted_password:
                                raise RuntimeError("Mercedes credentials are not configured")
                            password = repo.decrypt_password(row)
                    await session.commit()
                if provider._token_store._token is None:  # noqa: SLF001
                    await provider.login(username, password)
                states = await provider.discover()
                await self._persist_vehicle_states(runtime.site_id, states, provider=provider if isinstance(provider, MercedesProvider) else None)
                if isinstance(provider, MercedesProvider) and provider._token_store._token is not None:  # noqa: SLF001
                    async with self._session_factory() as session:
                        repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                        row = await repo.get_for_site(runtime.site_id)
                        if row is not None:
                            bundle = provider._token_store._token  # noqa: SLF001
                            if bundle.session_id and bundle.session_id != (row.session_id or ""):
                                await repo.persist_token_bundle(row, bundle)
                                await session.commit()
            elif isinstance(provider, MockVehicleProvider):
                await provider.connect()

            refresh_task = None
            watch_task = None
            if isinstance(provider, MercedesProvider):
                refresh_task = asyncio.create_task(self._periodic_rest_refresh(runtime, provider))
                watch_task = asyncio.create_task(self._connection_watch(runtime, provider))

            try:
                if watch_task is not None:
                    await watch_task
                else:
                    async for event in provider.watch_vehicle_state():
                        await self._persist_vehicle_states(runtime.site_id, (event.state,), provider=provider)
            finally:
                if refresh_task is not None:
                    refresh_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await refresh_task
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Vehicle integration failed for site %s: %s", runtime.site_slug, exc)
            async with self._session_factory() as session:
                repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                row = await repo.get_for_site(runtime.site_id)
                if row is not None:
                    await repo.update_runtime_status(
                        row,
                        connection_state=VehicleConnectionState.BACKOFF.value,
                        last_error=str(exc)[:512],
                    )
                    await session.commit()
        finally:
            with suppress(Exception):
                await runtime.provider.close()
            runtime = self._runtimes.get(site_id)
            if runtime is not None:
                runtime.task = None

    async def _connection_watch(self, runtime: _SiteRuntime, provider: MercedesProvider) -> None:
        manager = provider.connection_manager

        async def connect() -> None:
            await provider.connect()

        async def watch() -> None:
            async for event in provider.watch_vehicle_state():
                await self._persist_vehicle_states(runtime.site_id, (event.state,), provider=provider)

        await manager.run(connect=connect, watch=watch)
        await self._persist_connection_status(runtime.site_id, provider)

    async def _persist_connection_status(self, site_id: int, provider: MercedesProvider) -> None:
        status = provider.connection_manager.status
        async with self._session_factory() as session:
            repo = VehicleProviderRepository(session, secret_box=self._secret_box)
            row = await repo.get_for_site(site_id)
            if row is None:
                return
            await repo.update_runtime_status(
                row,
                connection_state=status.connection_state.value,
                last_error=status.last_error,
                backoff_until=status.backoff_until,
                blocked_since=status.blocked_since,
                reconnect_count=status.reconnect_count,
                http_429_count=status.http_429_count,
                decode_failure_count=status.decode_failure_count,
            )
            await session.commit()

    async def _persist_vehicle_states(
        self,
        site_id: int,
        states: tuple[VehicleState, ...],
        *,
        provider: MercedesProvider | MockVehicleProvider | None = None,
    ) -> None:
        if not states:
            return
        async with self._session_factory() as session:
            vehicle_repo = VehicleRepository(session, is_sqlite=self._settings.is_sqlite)
            provider_repo = VehicleProviderRepository(session, secret_box=self._secret_box)
            for state in states:
                existing = await vehicle_repo.get_by_external_id(
                    site_id=site_id,
                    provider=state.provider,
                    external_id=state.vehicle_id,
                )
                if existing is not None and not existing.enabled:
                    continue
                db_vehicle = await vehicle_repo.upsert_vehicle(
                    site_id=site_id,
                    provider=state.provider,
                    external_id=state.vehicle_id,
                    vin=state.vin,
                    manufacturer=state.manufacturer,
                    model=state.model,
                    display_name=state.model,
                )
                await vehicle_repo.upsert_capabilities(db_vehicle.id, state.capabilities)
                await vehicle_repo.persist_state(db_vehicle.id, state)
                if isinstance(provider, MercedesProvider):
                    observations = provider.mapper.attribute_recorder.drain()
                    if observations:
                        await VehicleAttributeObservationRepository(
                            session,
                            is_sqlite=self._settings.is_sqlite,
                        ).record_observations(db_vehicle.id, observations)
                await VehicleHaloCorrelationRepository(session).correlate_and_persist(db_vehicle, state)
            conn = await provider_repo.get_for_site(site_id)
            if conn is not None:
                await provider_repo.update_runtime_status(
                    conn,
                    connection_state=VehicleConnectionState.CONNECTED.value,
                    last_error="",
                    last_success_at=datetime.now(UTC),
                    reset_consecutive_failures=True,
                    last_latency_ms=(
                        getattr(provider.rest_client.api_client, "last_latency_ms", None)
                        if isinstance(provider, MercedesProvider)
                        else None
                    ),
                )
            await session.commit()

    async def _periodic_rest_refresh(self, runtime: _SiteRuntime, provider: MercedesProvider) -> None:
        planner = AdaptivePollingPlanner()
        while True:
            latest_state = next(iter(provider._vehicles.values()), None)  # noqa: SLF001
            db_latest = None
            polling_context = _PollingContext()
            async with self._session_factory() as session:
                vehicle_repo = VehicleRepository(session, is_sqlite=self._settings.is_sqlite)
                correlation_repo = VehicleHaloCorrelationRepository(session)
                vehicles = await vehicle_repo.list_for_site(runtime.site_id)
                if vehicles:
                    db_latest = await vehicle_repo.get_latest_state(vehicles[0].id)
                    correlation = await correlation_repo.get(vehicles[0].id)
                    vehicle = await vehicle_repo.get(vehicles[0].id)
                    charger = await correlation_repo.resolve_charger(vehicle) if vehicle else None
                    polling_context = _build_polling_context(db_latest, latest_state, correlation, charger)
                row = await VehicleProviderRepository(session, secret_box=self._secret_box).get_for_site(runtime.site_id)
                if row is not None:
                    await session.commit()

            decision = planner.decide(
                is_charging=polling_context.is_charging,
                is_plugged_in=polling_context.is_plugged_in,
                charging_power_kw=polling_context.charging_power_kw,
                last_vehicle_update=polling_context.last_vehicle_update,
                soc_updated_at=polling_context.soc_updated_at,
                missing_gps=polling_context.missing_gps,
                away_from_home=polling_context.away_from_home,
            )
            async with self._session_factory() as session:
                repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                row = await repo.get_for_site(runtime.site_id)
                if row is not None:
                    await repo.update_runtime_status(
                        row,
                        current_polling_interval_seconds=decision.interval_seconds,
                    )
                    await session.commit()
            try:
                states = await provider.sync_from_rest()
                if decision.mode.value == "POSITION_RECOVERY":
                    for state in states:
                        if state.latitude is not None and state.longitude is not None:
                            logger.info(
                                "Mercedes GPS recovered via REST for site %s (%.5f, %.5f)",
                                runtime.site_slug,
                                state.latitude,
                                state.longitude,
                            )
                await self._persist_vehicle_states(runtime.site_id, states, provider=provider)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Mercedes periodic REST refresh failed for site %s", runtime.site_slug)
                async with self._session_factory() as session:
                    repo = VehicleProviderRepository(session, secret_box=self._secret_box)
                    row = await repo.get_for_site(runtime.site_id)
                    if row is not None:
                        await repo.update_runtime_status(
                            row,
                            last_failure_at=datetime.now(UTC),
                            consecutive_failures=(row.consecutive_failures or 0) + 1,
                            last_error=str(exc)[:512],
                        )
                        await session.commit()
            await asyncio.sleep(decision.interval_seconds)

    async def _stop_site(self, runtime: _SiteRuntime) -> None:
        if runtime.task is not None:
            runtime.task.cancel()
            with suppress(asyncio.CancelledError):
                await runtime.task
        with suppress(Exception):
            await runtime.provider.close()
