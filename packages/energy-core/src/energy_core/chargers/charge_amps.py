"""Charge Amps adapters (External API v5 + web app API + mock fallback)."""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.charge_amps_web import ChargeAmpsWebController
from energy_core.chargers.client import CHARGEAMPS_API_BASE, DEFAULT_CONNECTOR_ID
from energy_core.chargers.halo_adapter import ChargeAmpsHaloAdapter, build_halo_adapter
from energy_core.chargers.mock import MockChargeAmpsController

logger = logging.getLogger(__name__)

__all__ = [
    "CHARGEAMPS_API_BASE",
    "DEFAULT_CONNECTOR_ID",
    "ChargeAmpsController",
    "ChargeAmpsExternalController",
    "ChargeAmpsHaloController",
    "build_chargeamps_controller",
]


class ChargeAmpsController(Protocol):
    async def get_status(self) -> ChargerStatus: ...

    async def set_current_limit(self, amps: float) -> None: ...

    async def start_charging(self) -> None: ...

    async def stop_charging(self) -> None: ...

    async def is_connected(self) -> bool: ...

    async def is_vehicle_connected(self) -> bool: ...


class ChargeAmpsExternalController:
    """Control Charge Amps Halo via the official External REST API (v5)."""

    def __init__(
        self,
        charger_id: str,
        *,
        api_key: str = "",
        email: str = "",
        password: str = "",
        connector_id: int = DEFAULT_CONNECTOR_ID,
        use_mock: bool | None = None,
        min_current_a: float = 6.0,
        max_current_a: float = 16.0,
        phases: int = 3,
    ) -> None:
        self.charger_id = charger_id
        self._connector_id = connector_id
        self._api_key = api_key or os.getenv("CHARGEAMPS_API_KEY", "")
        self._email = email or os.getenv("CHARGEAMPS_EMAIL", "")
        self._password = password or os.getenv("CHARGEAMPS_PASSWORD", "")
        env_mock = os.getenv("CHARGEAMPS_MOCK", "true").lower() in {"1", "true", "yes"}
        self._use_mock = env_mock if use_mock is None else use_mock
        self._mock = MockChargeAmpsController(charger_id)
        self._adapter: ChargeAmpsHaloAdapter | None = None
        self._web_status: ChargeAmpsWebController | None = None
        if not self._use_mock and self._api_key:
            self._adapter = build_halo_adapter(
                charger_id,
                api_key=self._api_key,
                email=self._email,
                password=self._password,
                connector_id=connector_id,
                min_current_a=min_current_a,
                max_current_a=max_current_a,
                phases=phases,
            )
        if not self._use_mock and self._email and self._password:
            self._web_status = ChargeAmpsWebController(
                charger_id,
                email=self._email,
                password=self._password,
                connector_id=connector_id,
                use_mock=False,
            )

    async def get_status(self) -> ChargerStatus:
        if self._adapter is None:
            return await self._mock.get_status()
        status = await self._adapter.get_status()
        if status.vehicle_connected or self._web_status is None:
            return status
        web_status = await self._web_status.get_status()
        if not web_status.vehicle_connected:
            return status
        return ChargerStatus(
            connected=status.connected,
            vehicle_connected=True,
            current_limit_a=status.current_limit_a,
            charging=status.charging or web_status.charging,
        )

    async def set_current_limit(self, amps: float) -> None:
        if self._adapter is None:
            await self._mock.set_current_limit(amps)
            return
        await self._adapter.set_current_limit(amps)

    async def start_charging(self) -> None:
        if self._adapter is None:
            await self._mock.start_charging()
            return
        await self._adapter.start_charging()

    async def stop_charging(self) -> None:
        if self._adapter is None:
            await self._mock.stop_charging()
            return
        await self._adapter.stop_charging()

    async def is_connected(self) -> bool:
        status = await self.get_status()
        return status.connected

    async def is_vehicle_connected(self) -> bool:
        status = await self.get_status()
        return status.vehicle_connected

    async def _connector_settings(self) -> dict[str, Any]:
        if self._adapter is None:
            raise RuntimeError("Connector settings unavailable in mock mode")
        return await self._adapter._client.get_connector_settings(force=True)

    async def _request(
        self, method: str, path: str, *, json_body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if self._adapter is None:
            raise RuntimeError("Direct request unavailable in mock mode")
        return await self._adapter._client._request(method, path, json_body=json_body)


ChargeAmpsHaloController = ChargeAmpsExternalController


def _resolve_provider(api_key: str, email: str, password: str) -> str:
    if api_key:
        return "external"
    provider = os.getenv("CHARGEAMPS_PROVIDER", "").strip().lower()
    if provider in {"web", "external"}:
        return provider
    if email and password:
        return "web"
    return "mock"


def build_chargeamps_controller(
    charger_id: str,
    *,
    api_key: str = "",
    email: str = "",
    password: str = "",
    use_mock: bool | None = None,
    min_current_a: float = 6.0,
    max_current_a: float = 16.0,
    phases: int = 3,
) -> ChargeAmpsController:
    resolved_api_key = api_key or os.getenv("CHARGEAMPS_API_KEY", "")
    resolved_email = email or os.getenv("CHARGEAMPS_EMAIL", "")
    resolved_password = password or os.getenv("CHARGEAMPS_PASSWORD", "")
    provider = _resolve_provider(resolved_api_key, resolved_email, resolved_password)

    if provider == "web":
        logger.debug("chargeamps provider=web charger_id=%s", charger_id)
        return ChargeAmpsWebController(
            charger_id,
            email=resolved_email,
            password=resolved_password,
            use_mock=use_mock,
        )

    return ChargeAmpsExternalController(
        charger_id,
        api_key=resolved_api_key,
        email=resolved_email,
        password=resolved_password,
        use_mock=use_mock,
        min_current_a=min_current_a,
        max_current_a=max_current_a,
        phases=phases,
    )
