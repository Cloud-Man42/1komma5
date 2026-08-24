"""Mercedes websocket transport."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosed

from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenStore
from energy_core.vehicles.mercedes.constants import websocket_url
from energy_core.vehicles.mercedes.protocol.decoder import MercedesMessageDecoder

logger = logging.getLogger(__name__)


class MercedesWebSocketClient:
    def __init__(
        self,
        *,
        region: str,
        token_store: MercedesTokenStore,
        app_version: MercedesAppVersionManager,
        decoder: MercedesMessageDecoder | None = None,
    ) -> None:
        self._region = region
        self._token_store = token_store
        self._app_version = app_version
        self._decoder = decoder or MercedesMessageDecoder()
        self._connection = None
        self._closed = False

    @property
    def decoder(self) -> MercedesMessageDecoder:
        return self._decoder

    async def connect(self) -> None:
        access_token = await self._token_store.get_valid_access_token()
        session_id = self._token_store.session_id
        headers = self._app_version.websocket_headers(session_id, access_token)
        self._connection = await websockets.connect(
            websocket_url(self._region),
            additional_headers=headers,
            ping_interval=30,
            ping_timeout=32,
            close_timeout=5,
        )
        self._closed = False
        logger.info("Mercedes websocket connected")

    async def messages(self) -> AsyncIterator[bytes]:
        if self._connection is None:
            raise RuntimeError("Mercedes websocket is not connected")
        try:
            async for frame in self._connection:
                if isinstance(frame, bytes):
                    yield frame
        except ConnectionClosed:
            logger.info("Mercedes websocket disconnected")
            raise

    async def send(self, payload: bytes) -> None:
        if self._connection is None:
            raise RuntimeError("Mercedes websocket is not connected")
        await self._connection.send(payload)

    async def close(self) -> None:
        self._closed = True
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
