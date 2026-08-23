"""Charge Amps user-app API adapter (my.charge.space)."""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.mock import MockChargeAmpsController
from energy_core.chargers.vehicle_status import vehicle_connected_from_web_connector

logger = logging.getLogger(__name__)

CHARGEAMPS_WEB_BASE = "https://my.charge.space/api"
CHARGEAMPS_WEB_ORIGIN = "https://my.charge.space"
DEFAULT_CONNECTOR_ID = 1
DEFAULT_RFID_TAG = "999999"


class ChargeAmpsWebController:
    """Control Charge Amps Halo via the my.charge.space web API."""

    def __init__(
        self,
        charger_id: str,
        *,
        email: str = "",
        password: str = "",
        connector_id: int = DEFAULT_CONNECTOR_ID,
        use_mock: bool | None = None,
    ) -> None:
        self.charger_id = charger_id
        self._connector_id = connector_id
        self._email = email or os.getenv("CHARGEAMPS_EMAIL", "")
        self._password = password or os.getenv("CHARGEAMPS_PASSWORD", "")
        env_mock = os.getenv("CHARGEAMPS_MOCK", "true").lower() in {"1", "true", "yes"}
        self._use_mock = env_mock if use_mock is None else use_mock
        self._mock = MockChargeAmpsController(charger_id)
        self._token: str | None = None
        self._user_id: str | None = None
        self._default_rfid_tag: str | None = None

    async def get_status(self) -> ChargerStatus:
        if self._use_mock or not self._has_credentials():
            return await self._mock.get_status()
        data = await self._request("GET", f"/chargepoints/{self.charger_id}")
        connectors = data.get("connectors") or []
        connector = _connector_by_id(connectors, self._connector_id)
        if connector is None:
            return ChargerStatus(
                connected=True,
                vehicle_connected=False,
                current_limit_a=None,
                charging=False,
            )

        self._default_rfid_tag = _valid_rfid_tag(connector.get("defaultNfcTagId"))
        ocpp_status = str(connector.get("ocppStatus") or "")
        current_a = _float_or_none(connector.get("userCurrent"))
        if current_a is None:
            current_a = _float_or_none(connector.get("currentCurrent"))

        return ChargerStatus(
            connected=_is_online(data),
            vehicle_connected=vehicle_connected_from_web_connector(connector),
            current_limit_a=current_a,
            charging=bool(connector.get("isCharging")) or ocpp_status == "Charging",
        )

    async def set_current_limit(self, amps: float) -> None:
        if self._use_mock or not self._has_credentials():
            await self._mock.set_current_limit(amps)
            return
        params = {f"userCurrentConnector{self._connector_id}": _current_param(amps)}
        await self._request(
            "PUT",
            f"/chargepoints/{self.charger_id}/updateusersettings",
            params=params,
        )

    async def start_charging(self) -> None:
        if self._use_mock or not self._has_credentials():
            await self._mock.start_charging()
            return
        status = await self.get_status()
        if status.charging:
            logger.debug(
                "chargeamps web skip remotestart already charging charger_id=%s",
                self.charger_id,
            )
            return
        rfid_tag = await self._resolve_rfid_tag()
        try:
            await self._request(
                "PUT",
                f"/chargepoints/{self.charger_id}/{self._connector_id}/remotestart",
                params={"rfidTag": rfid_tag},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {400, 409}:
                logger.debug(
                    "chargeamps web remotestart ignored charger_id=%s status=%s tag=%s",
                    self.charger_id,
                    exc.response.status_code,
                    rfid_tag,
                )
                return
            raise

    async def stop_charging(self) -> None:
        if self._use_mock or not self._has_credentials():
            await self._mock.stop_charging()
            return
        status = await self.get_status()
        await self.set_current_limit(0)
        if not status.charging:
            return
        user_id = await self._ensure_user_id()
        try:
            await self._request(
                "PUT",
                f"/chargepoints/{self.charger_id}/{self._connector_id}/remotestop",
                params={"userId": user_id},
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {400, 404, 409}:
                raise
            logger.debug(
                "chargeamps web remotestop ignored charger_id=%s status=%s",
                self.charger_id,
                exc.response.status_code,
            )

    async def is_connected(self) -> bool:
        status = await self.get_status()
        return status.connected

    async def is_vehicle_connected(self) -> bool:
        status = await self.get_status()
        return status.vehicle_connected

    def _has_credentials(self) -> bool:
        return bool(self._email and self._password)

    async def _resolve_rfid_tag(self) -> str:
        env_tag = _valid_rfid_tag(os.getenv("CHARGEAMPS_RFID_TAG"))
        if env_tag:
            return env_tag
        if self._default_rfid_tag:
            return self._default_rfid_tag

        for path in (
            f"/chargepoints/{self.charger_id}/{self._connector_id}/remotestart/tags",
            "/users/nfctags/own",
        ):
            tag = await self._first_active_rfid_tag(path)
            if tag:
                self._default_rfid_tag = tag
                return tag

        return DEFAULT_RFID_TAG

    async def _first_active_rfid_tag(self, path: str) -> str | None:
        data = await self._request_json("GET", path)
        if not isinstance(data, list):
            return None
        for item in data:
            if not isinstance(item, dict):
                continue
            tag_id = _valid_rfid_tag(item.get("id"))
            if tag_id and item.get("active", True):
                return tag_id
        return None

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        token = await self._ensure_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": CHARGEAMPS_WEB_ORIGIN,
            "Accept": "application/json",
        }
        url = f"{CHARGEAMPS_WEB_BASE}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.request(
                method, url, headers=headers, params=params, json=json_body
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    async def _default_rfid_tag_for_connector(self) -> str:
        return await self._resolve_rfid_tag()

    async def _ensure_user_id(self) -> str:
        if self._user_id:
            return self._user_id
        token = await self._ensure_token()
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        user_id = claims.get("unique_name") or claims.get("sub")
        if not user_id:
            raise RuntimeError("Charge Amps web login token missing user id")
        self._user_id = str(user_id)
        return self._user_id

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = await self._request_json(method, path, params=params, json_body=json_body)
        return data if isinstance(data, dict) else {}

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token
        if not self._has_credentials():
            raise RuntimeError("Charge Amps web credentials missing")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{CHARGEAMPS_WEB_BASE}/auth/login",
                headers={"Origin": CHARGEAMPS_WEB_ORIGIN, "Accept": "application/json"},
                json={"email": self._email, "password": self._password},
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("token") if isinstance(data, dict) else None
            if not token:
                raise RuntimeError("Charge Amps web login failed")
            self._token = str(token)
            return self._token


def _connector_by_id(connectors: list[Any], connector_id: int) -> dict[str, Any] | None:
    for connector in connectors:
        if isinstance(connector, dict) and connector.get("connectorId") == connector_id:
            return connector
    return None


def _is_online(data: dict[str, Any]) -> bool:
    status = str(data.get("chargePointStatus") or "")
    if status.lower() == "offline":
        return False
    return bool(data.get("ip") or status)


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _current_param(amps: float) -> int:
    """Charge Amps web API rejects float query values (e.g. 16.0)."""
    return max(0, int(round(amps)))


def _valid_rfid_tag(value: Any) -> str | None:
    if value is None:
        return None
    tag = str(value).strip()
    if not tag or all(ch == "0" for ch in tag):
        return None
    return tag
