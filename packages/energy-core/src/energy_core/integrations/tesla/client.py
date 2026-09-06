"""Tesla Fleet API client."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from energy_core.integrations.tesla.config import fleet_api_base_url
from energy_core.integrations.tesla.parsing import parse_vehicle_state
from energy_core.vehicles.abstractions.models import VehicleState

logger = logging.getLogger(__name__)
TESLA_AUTH_URL = "https://auth.tesla.com/oauth2/v3/token"


class TeslaApiError(Exception):
    pass


class TeslaFleetClient:
    def __init__(
        self,
        *,
        region: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._region = region
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._timeout = timeout_seconds
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _ensure_token(self, client: httpx.AsyncClient) -> str:
        now = datetime.now(UTC)
        if self._access_token and self._token_expires_at and now < self._token_expires_at:
            return self._access_token
        response = await client.post(
            TESLA_AUTH_URL,
            json={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )
        if response.status_code >= 400:
            raise TeslaApiError(f"Tesla auth failed with status {response.status_code}")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise TeslaApiError("Tesla auth response missing access_token")
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_token = str(token)
        self._token_expires_at = now + timedelta(seconds=max(60, expires_in - 60))
        return self._access_token

    async def _authorized_request(self, method: str, path: str) -> httpx.Response:
        base_url = fleet_api_base_url(self._region)
        async with httpx.AsyncClient(base_url=base_url, timeout=self._timeout) as auth_client:
            token = await self._ensure_token(auth_client)
        async with httpx.AsyncClient(base_url=base_url, timeout=self._timeout) as client:
            return await client.request(
                method,
                path,
                headers={"Authorization": f"Bearer {token}"},
            )

    async def list_vehicles(self) -> list[dict[str, Any]]:
        response = await self._authorized_request("GET", "/api/1/vehicles")
        if response.status_code >= 400:
            raise TeslaApiError(f"Tesla vehicle list failed with status {response.status_code}")
        payload = response.json()
        response_data = payload.get("response")
        if isinstance(response_data, list):
            return response_data
        return []

    async def get_vehicle_data(self, vehicle_id: str) -> dict[str, Any]:
        response = await self._authorized_request("GET", f"/api/1/vehicles/{vehicle_id}/vehicle_data")
        if response.status_code >= 400:
            raise TeslaApiError(f"Tesla vehicle data failed with status {response.status_code}")
        payload = response.json()
        response_data = payload.get("response")
        if isinstance(response_data, dict):
            return response_data
        return {}

    async def get_vehicle_states(self) -> tuple[VehicleState, ...]:
        vehicles = await self.list_vehicles()
        states: list[VehicleState] = []
        for vehicle in vehicles:
            vehicle_id = str(vehicle.get("id_s") or vehicle.get("id") or "")
            if not vehicle_id:
                continue
            data = await self.get_vehicle_data(vehicle_id)
            merged = {**vehicle, **data}
            states.append(parse_vehicle_state(merged))
        return tuple(states)
