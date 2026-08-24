"""Mercedes connection lifecycle with backoff, watchdogs and circuit breaker."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from energy_core.vehicles.abstractions.models import VehicleConnectionState
from energy_core.vehicles.mercedes.auth.errors import MercedesAuthError
from energy_core.vehicles.mercedes.transport.backoff import MercedesBackoffPolicy

logger = logging.getLogger(__name__)

CONNECTION_WATCHDOG_SECONDS = 30
PING_WATCHDOG_SECONDS = 32
RECONNECT_WATCHDOG_SECONDS = 60
CIRCUIT_BREAKER_AUTH_FAILURES = 5


@dataclass
class ConnectionManagerStatus:
    connection_state: VehicleConnectionState = VehicleConnectionState.DISCONNECTED
    last_message_at: datetime | None = None
    last_ping_at: datetime | None = None
    reconnect_count: int = 0
    http_429_count: int = 0
    decode_failure_count: int = 0
    blocked_since: datetime | None = None
    backoff_until: datetime | None = None
    last_error: str = ""
    last_error_at: datetime | None = None
    circuit_open: bool = False
    auth_failure_count: int = 0


class MercedesConnectionManager:
    """Coordinates connect/reconnect with exponential backoff and circuit breaker."""

    def __init__(self) -> None:
        self._backoff = MercedesBackoffPolicy()
        self._status = ConnectionManagerStatus()
        self._running = False
        self._connect_fn = None
        self._watch_fn = None
        self._task: asyncio.Task | None = None
        self._last_frame_at: datetime | None = None
        self._manual_reset = False

    @property
    def status(self) -> ConnectionManagerStatus:
        return self._status

    def reset_circuit(self) -> None:
        self._manual_reset = True
        self._status.circuit_open = False
        self._status.auth_failure_count = 0
        self._backoff.reset()
        self._status.blocked_since = None

    async def run(
        self,
        *,
        connect: Callable[[], Awaitable[None]],
        watch: Callable[[], Awaitable[None]],
    ) -> None:
        self._connect_fn = connect
        self._watch_fn = watch
        self._running = True
        while self._running:
            if self._status.circuit_open and not self._manual_reset:
                await asyncio.sleep(5)
                continue
            self._manual_reset = False
            if self._status.backoff_until and datetime.now(UTC) < self._status.backoff_until:
                await asyncio.sleep(1)
                continue
            try:
                self._status.connection_state = VehicleConnectionState.CONNECTING
                await self._connect_fn()
                self._status.connection_state = VehicleConnectionState.CONNECTED
                self._backoff.on_success()
                self._status.backoff_until = None
                self._status.blocked_since = None
                self._status.auth_failure_count = 0
                self._last_frame_at = datetime.now(UTC)
                self._status.last_ping_at = self._last_frame_at
                await self._watch_with_watchdogs()
            except asyncio.CancelledError:
                raise
            except MercedesAuthError as exc:
                await self._handle_auth_failure(str(exc))
            except Exception as exc:
                await self._handle_transport_failure(exc)

    async def _watch_with_watchdogs(self) -> None:
        assert self._watch_fn is not None
        watch_task = asyncio.create_task(self._watch_fn())
        try:
            while self._running and not watch_task.done():
                now = datetime.now(UTC)
                if self._last_frame_at and (now - self._last_frame_at).total_seconds() > CONNECTION_WATCHDOG_SECONDS:
                    raise TimeoutError("Mercedes connection watchdog expired")
                if self._status.last_ping_at and (now - self._status.last_ping_at).total_seconds() > PING_WATCHDOG_SECONDS:
                    raise TimeoutError("Mercedes ping watchdog expired")
                await asyncio.sleep(1)
            await watch_task
        finally:
            if not watch_task.done():
                watch_task.cancel()
                with suppress(asyncio.CancelledError):
                    await watch_task

    def record_frame(self) -> None:
        now = datetime.now(UTC)
        self._last_frame_at = now
        self._status.last_message_at = now
        self._status.last_ping_at = now

    def record_decode_failure(self) -> None:
        self._status.decode_failure_count += 1

    async def _handle_auth_failure(self, message: str) -> None:
        self._status.auth_failure_count += 1
        self._status.last_error = message
        self._status.last_error_at = datetime.now(UTC)
        self._status.connection_state = VehicleConnectionState.BACKOFF
        if self._status.auth_failure_count >= CIRCUIT_BREAKER_AUTH_FAILURES:
            self._status.circuit_open = True
            logger.warning("Mercedes circuit breaker opened after repeated auth failures")
            return
        decision = self._backoff.on_failure()
        self._status.backoff_until = self._backoff.backoff_until(decision)
        self._status.reconnect_count += 1
        await asyncio.sleep(decision.delay_seconds)

    async def _handle_transport_failure(self, exc: Exception) -> None:
        message = str(exc)
        self._status.last_error = message
        self._status.last_error_at = datetime.now(UTC)
        self._status.reconnect_count += 1
        if "429" in message:
            self._status.http_429_count += 1
            if self._status.blocked_since is None:
                self._status.blocked_since = datetime.now(UTC)
            decision = self._backoff.on_rate_limited()
        else:
            self._status.connection_state = VehicleConnectionState.RECONNECTING
            decision = self._backoff.on_failure()
        self._status.backoff_until = self._backoff.backoff_until(decision)
        logger.info("Mercedes reconnect scheduled in %.0fs", decision.delay_seconds)
        await asyncio.sleep(decision.delay_seconds)

    def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
