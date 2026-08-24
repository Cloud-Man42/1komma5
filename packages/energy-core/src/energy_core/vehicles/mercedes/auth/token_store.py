"""In-memory Mercedes token cache with refresh locking."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from energy_core.vehicles.mercedes.auth.login import MercedesLoginFlow, is_token_expired

logger = logging.getLogger(__name__)


@dataclass
class MercedesTokenBundle:
    access_token: str
    refresh_token: str
    expires_at: int
    device_guid: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()).upper())

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, device_guid: str, session_id: str | None = None) -> MercedesTokenBundle:
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=int(data["expires_at"]),
            device_guid=device_guid,
            session_id=session_id or str(uuid.uuid4()).upper(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }


class MercedesTokenStore:
    def __init__(
        self,
        *,
        login_flow: MercedesLoginFlow,
        persist: Callable[[MercedesTokenBundle], Awaitable[None]] | None = None,
    ) -> None:
        self._login_flow = login_flow
        self._persist = persist
        self._token: MercedesTokenBundle | None = None
        self._lock = asyncio.Lock()

    @property
    def device_guid(self) -> str:
        return self._login_flow._device_guid  # noqa: SLF001

    def load(self, bundle: MercedesTokenBundle | None) -> None:
        if bundle is not None:
            self._ensure_session_id(bundle)
        self._token = bundle

    def _ensure_session_id(self, bundle: MercedesTokenBundle) -> None:
        if not (bundle.session_id or "").strip():
            bundle.session_id = str(uuid.uuid4()).upper()

    async def get_valid_access_token(self) -> str:
        async with self._lock:
            if self._token is None:
                raise RuntimeError("Mercedes is not authenticated")
            if not is_token_expired(self._token.to_dict()):
                return self._token.access_token
            refreshed = await self._login_flow.refresh_access_token(self._token.refresh_token)
            self._token = MercedesTokenBundle.from_dict(
                refreshed,
                device_guid=self._token.device_guid,
                session_id=self._token.session_id,
            )
            if self._persist:
                await self._persist(self._token)
            return self._token.access_token

    async def store_login(self, token_info: dict[str, Any]) -> MercedesTokenBundle:
        bundle = MercedesTokenBundle.from_dict(token_info, device_guid=self._login_flow._device_guid)  # noqa: SLF001
        self._ensure_session_id(bundle)
        self._token = bundle
        if self._persist:
            await self._persist(bundle)
        return bundle

    @property
    def session_id(self) -> str:
        if self._token is None:
            return str(uuid.uuid4()).upper()
        self._ensure_session_id(self._token)
        return self._token.session_id
