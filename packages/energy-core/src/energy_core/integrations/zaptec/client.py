"""Zaptec Cloud REST client."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from energy_core.integrations.zaptec.constants import ZAPTEC_API_BASE, ZAPTEC_TOKEN_URL
from energy_core.integrations.zaptec.parsing import parse_charger_status
from energy_core.integrations.zaptec.types import ZaptecChargerStatus

logger = logging.getLogger(__name__)


class ZaptecApiError(Exception):
    pass


class ZaptecRestClient:
    def __init__(
        self,
        *,
        username: str,
        password: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._username = username
        self._password = password
        self._timeout = timeout_seconds
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        now = datetime.now(UTC)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token
        response = await client.post(
            ZAPTEC_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            raise ZaptecApiError(f"Zaptec auth failed with status {response.status_code}")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise ZaptecApiError("Zaptec auth response missing access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        self._token = str(token)
        self._token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return self._token

    async def _authorized_request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(base_url=ZAPTEC_API_BASE, timeout=self._timeout) as client:
            token = await self._ensure_token(client)
            response = await client.request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {token}"},
            )
        return response

    async def get_charger_state(self, charger_id: str) -> list[dict[str, Any]]:
        response = await self._authorized_request("GET", f"/api/chargers/{charger_id}/state")
        if response.status_code == 404:
            raise ZaptecApiError(f"Zaptec charger '{charger_id}' not found")
        if response.status_code >= 400:
            raise ZaptecApiError(f"Zaptec state request failed with status {response.status_code}")
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return []

    async def send_charger_command(self, charger_id: str, command_id: int) -> None:
        response = await self._authorized_request(
            "POST",
            f"/api/chargers/{charger_id}/sendCommand/{command_id}",
        )
        if response.status_code >= 400:
            raise ZaptecApiError(
                f"Zaptec command {command_id} failed with status {response.status_code}"
            )

    async def set_installation_available_current(
        self,
        installation_id: str,
        *,
        available_current_a: float,
    ) -> None:
        response = await self._authorized_request(
            "POST",
            f"/api/installation/{installation_id}/update",
            json={"availableCurrent": available_current_a},
        )
        if response.status_code >= 400:
            raise ZaptecApiError(
                f"Zaptec installation update failed with status {response.status_code}"
            )

    async def stop_charging(self, charger_id: str) -> None:
        from energy_core.integrations.zaptec.constants import COMMAND_STOP_CHARGING_FINAL

        await self.send_charger_command(charger_id, COMMAND_STOP_CHARGING_FINAL)

    async def resume_charging(self, charger_id: str) -> None:
        from energy_core.integrations.zaptec.constants import COMMAND_RESUME_CHARGING

        await self.send_charger_command(charger_id, COMMAND_RESUME_CHARGING)

    async def get_charger_status(self, charger_id: str) -> ZaptecChargerStatus:
        observations = await self.get_charger_state(charger_id)
        return parse_charger_status(observations)

    async def test_connection(self, charger_id: str) -> ZaptecChargerStatus:
        return await self.get_charger_status(charger_id)
