"""Mercedes provider orchestrating auth, REST, websocket and mapping."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime

from energy_core.vehicles.abstractions.models import VehicleConnectionState, VehicleState, VehicleStateChangedEvent
from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.login import MercedesLoginFlow
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle, MercedesTokenStore
from energy_core.vehicles.mercedes.commands.response import MercedesCommandStatus, parse_command_status
from energy_core.vehicles.mercedes.mapping.vehicle_mapper import MercedesCapabilityMapper, MercedesVehicleMapper
from energy_core.vehicles.mercedes.protocol.decoder import MercedesMessageDecoder
from energy_core.vehicles.mercedes.transport.backoff import MercedesBackoffPolicy
from energy_core.vehicles.mercedes.transport.connection_manager import MercedesConnectionManager
from energy_core.vehicles.mercedes.transport.rest_client import MercedesRestClient
from energy_core.vehicles.mercedes.transport.websocket_client import MercedesWebSocketClient
from energy_core.vehicles.vin import mask_vin

logger = logging.getLogger(__name__)


class MercedesProvider:
    provider_id = "mercedes"

    def __init__(
        self,
        *,
        region: str,
        device_guid: str | None = None,
        token_bundle: MercedesTokenBundle | None = None,
    ) -> None:
        self._region = region
        self._device_guid = device_guid or str(uuid.uuid4())
        self._app_version = MercedesAppVersionManager(region)
        self._login_flow = MercedesLoginFlow(region=region, device_guid=self._device_guid, app_version=self._app_version)
        self._token_store = MercedesTokenStore(login_flow=self._login_flow)
        if token_bundle is not None:
            self._token_store.load(token_bundle)
        self._rest = MercedesRestClient(
            region=region,
            token_store=self._token_store,
            app_version=self._app_version,
        )
        self._decoder = MercedesMessageDecoder()
        self._websocket: MercedesWebSocketClient | None = None
        self._mapper = MercedesVehicleMapper()
        self._vehicles: dict[str, VehicleState] = {}
        self._connected = False
        self._backoff = MercedesBackoffPolicy()
        self._subscribers: list[asyncio.Queue[VehicleStateChangedEvent | None]] = []
        self._watch_task: asyncio.Task | None = None
        self._connection_manager = MercedesConnectionManager()
        self.reconnect_count = 0
        self.http_429_count = 0

    @property
    def mapper(self) -> MercedesVehicleMapper:
        return self._mapper

    @property
    def connection_manager(self) -> MercedesConnectionManager:
        return self._connection_manager

    @property
    def token_store(self) -> MercedesTokenStore:
        return self._token_store

    @property
    def rest_client(self) -> MercedesRestClient:
        return self._rest

    @property
    def device_guid(self) -> str:
        return self._device_guid

    @property
    def connection_state(self) -> VehicleConnectionState:
        if not self._connected:
            return VehicleConnectionState.DISCONNECTED
        return VehicleConnectionState.CONNECTED

    async def login(self, email: str, password: str) -> MercedesTokenBundle:
        token_info = await self._login_flow.login(email, password)
        return await self._token_store.store_login(token_info)

    async def discover(self) -> tuple[VehicleState, ...]:
        if self._token_store._token is None:  # noqa: SLF001
            raise RuntimeError("Mercedes provider is not authenticated")
        await self._discover_vehicles()
        return await self.get_vehicles()

    async def connect(self) -> None:
        if self._token_store._token is None:  # noqa: SLF001
            raise RuntimeError("Mercedes provider is not authenticated")
        if not self._vehicles:
            await self._discover_vehicles()
        await self._app_version.refresh(self._rest.get_config, force=True)
        self._websocket = MercedesWebSocketClient(
            region=self._region,
            token_store=self._token_store,
            app_version=self._app_version,
            decoder=self._decoder,
        )
        await self._websocket.connect()
        self._connected = True
        self._backoff.on_success()
        await self._hydrate_vehicle_snapshots()

    async def _discover_vehicles(self) -> None:
        raw_vehicles = await self._rest.list_vehicles()
        discovered: dict[str, VehicleState] = {}
        for item in raw_vehicles:
            vin = str(item.get("vin") or item.get("finorvin") or item.get("fin") or "")
            vehicle_id = vin or str(item.get("id") or uuid.uuid4())
            model = str(item.get("model") or item.get("modelName") or "Mercedes-Benz")
            manufacturer = str(item.get("brand") or item.get("manufacturer") or "Mercedes-Benz")
            logger.info("Mercedes discovered vehicle %s", mask_vin(vin))
            caps_payload = await self._rest.get_capabilities(vin) if vin else {}
            command_caps = await self._rest.get_command_capabilities(vin) if vin else {}
            capabilities = MercedesCapabilityMapper.from_rest_payload(caps_payload, command_payload=command_caps)
            discovered[vehicle_id] = self._mapper.apply_discovery(
                vehicle_id=vehicle_id,
                vin=vin or None,
                manufacturer=manufacturer,
                model=model,
                capabilities=capabilities,
            )
        self._vehicles = discovered

    async def _hydrate_vehicle_snapshots(self, *, vins: tuple[str, ...] | None = None) -> None:
        vin_filter = set(vins) if vins else None
        for vehicle_id, state in list(self._vehicles.items()):
            vin = state.vin or vehicle_id
            if not vin:
                continue
            if vin_filter is not None and vin not in vin_filter:
                continue
            try:
                payload = await self._rest.get_vehicle_attributes(vin)
            except Exception as exc:
                logger.warning("Mercedes REST snapshot unavailable for %s: %s", mask_vin(vin), exc)
                continue
            message = self._decoder.decode_vehicle_status(payload)
            if message is None or not message.attributes:
                message = self._decoder.decode_vep_update(payload)
            if message is None or not message.attributes:
                message = self._decoder.decode(payload)
            if message is None:
                logger.warning(
                    "Mercedes REST snapshot for %s could not be decoded (%d bytes)",
                    mask_vin(vin),
                    len(payload),
                )
                continue
            if not message.attributes:
                logger.warning("Mercedes REST snapshot for %s contained no attributes", mask_vin(vin))
                continue
            updated = self._mapper.apply_push(state, message, source="REST")
            self._vehicles[vehicle_id] = updated
            logger.info("Mercedes hydrated snapshot for %s (soc=%s)", mask_vin(vin), updated.state_of_charge_percent)

    async def sync_from_rest(self, *, vins: tuple[str, ...] | None = None) -> tuple[VehicleState, ...]:
        """Fetch the latest vehicle attributes over REST and return normalized states."""
        if self._token_store._token is None:  # noqa: SLF001
            raise RuntimeError("Mercedes provider is not authenticated")
        if not self._vehicles:
            await self._discover_vehicles()
        await self._app_version.refresh(self._rest.get_config, force=True)
        await self._hydrate_vehicle_snapshots(vins=vins)
        return await self.get_vehicles()

    async def get_vehicles(self) -> tuple[VehicleState, ...]:
        if not self._vehicles:
            return ()
        now = datetime.now(UTC)
        return tuple(self._mapper.mark_stale(state) for state in self._vehicles.values())

    async def send_command(self, payload: bytes) -> None:
        if self._websocket is None:
            raise RuntimeError("Mercedes websocket is not connected")
        await self._websocket.send(payload)
        logger.info("Mercedes command sent (%d bytes)", len(payload))

    async def send_command_and_wait(
        self,
        payload: bytes,
        *,
        request_id: str,
        timeout_seconds: float = 45.0,
    ) -> MercedesCommandStatus:
        if self._websocket is None:
            raise RuntimeError("Mercedes websocket is not connected")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[MercedesCommandStatus] = loop.create_future()

        async def _listen() -> None:
            try:
                async for frame in self._websocket.messages():
                    status = parse_command_status(frame)
                    if status is None:
                        continue
                    if status.request_id and status.request_id != request_id:
                        continue
                    if not future.done():
                        future.set_result(status)
                        return
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)

        listener = asyncio.create_task(_listen())
        try:
            await self._websocket.send(payload)
            logger.info("Mercedes command sent (%d bytes), waiting for ack %s", len(payload), request_id[:8])
            return await asyncio.wait_for(future, timeout=timeout_seconds)
        finally:
            listener.cancel()
            with suppress(asyncio.CancelledError):
                await listener

    async def watch_vehicle_state(self) -> AsyncIterator[VehicleStateChangedEvent]:
        queue: asyncio.Queue[VehicleStateChangedEvent | None] = asyncio.Queue()
        self._subscribers.append(queue)
        if self._watch_task is None:
            self._watch_task = asyncio.create_task(self._watch_loop())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    async def run_connected_watch(self) -> None:
        """Process websocket frames until failure. Used by connection manager."""
        assert self._websocket is not None
        async for frame in self._websocket.messages():
            self._connection_manager.record_frame()
            message = self._decoder.decode(frame)
            if message is None:
                self._connection_manager.record_decode_failure()
                continue
            for vehicle_id, state in list(self._vehicles.items()):
                if message.vin and state.vin and message.vin != state.vin:
                    continue
                updated = self._mapper.apply_push(state, message, source="WS")
                previous = self._vehicles[vehicle_id]
                self._vehicles[vehicle_id] = updated
                event = VehicleStateChangedEvent(state=updated, previous_state=previous)
                for queue in self._subscribers:
                    await queue.put(event)

    async def _watch_loop(self) -> None:
        try:
            await self.run_connected_watch()
        except Exception:
            logger.exception("Mercedes watch loop failed")
            self._connected = False
            self.reconnect_count += 1
            for vehicle_id, state in self._vehicles.items():
                self._vehicles[vehicle_id] = replace(
                    state,
                    connection_state=VehicleConnectionState.RECONNECTING,
                )
            raise

    async def close(self) -> None:
        self._connected = False
        if self._watch_task is not None:
            self._watch_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._watch_task
            self._watch_task = None
        if self._websocket is not None:
            await self._websocket.close()
            self._websocket = None
        for queue in self._subscribers:
            await queue.put(None)
