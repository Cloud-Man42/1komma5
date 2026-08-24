"""Mercedes REST API client."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenStore
from energy_core.vehicles.mercedes.constants import rest_api_base

logger = logging.getLogger(__name__)


class MercedesRestClient:
    def __init__(
        self,
        *,
        region: str,
        token_store: MercedesTokenStore,
        app_version: MercedesAppVersionManager,
        timeout: float = 30.0,
    ) -> None:
        self._region = region
        self._token_store = token_store
        self._app_version = app_version
        self._timeout = timeout

    async def get_config(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/config")

    async def list_vehicles(self) -> list[dict[str, Any]]:
        vehicles: list[dict[str, Any]] = []
        try:
            vehicles = self._extract_vehicle_list(await self._request("GET", "/v2/vehicles"))
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code not in {404, 405}:
                raise
            logger.info("Mercedes /v2/vehicles unavailable (%s), falling back to masterdata", exc.response.status_code)
        if vehicles:
            return vehicles
        masterdata = await self._request("GET", "/v1/vehicle/self/masterdata")
        assigned = self._extract_vehicle_list(masterdata)
        if assigned:
            logger.info("Mercedes vehicle list loaded from masterdata (%d)", len(assigned))
        return assigned

    @staticmethod
    def _extract_vehicle_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("vehicles", "data", "assignedVehicles"):
            items = payload.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []

    async def get_capabilities(self, vin: str) -> dict[str, Any]:
        payload = await self._request("GET", f"/v1/vehicle/{vin}/capabilities")
        return payload if isinstance(payload, dict) else {}

    async def get_command_capabilities(self, vin: str) -> dict[str, Any]:
        payload = await self._request("GET", f"/v1/vehicle/{vin}/capabilities/commands")
        return payload if isinstance(payload, dict) else {}

    async def get_vehicle_attributes(self, vin: str) -> bytes:
        access_token = await self._token_store.get_valid_access_token()
        headers = self._app_version.webapi_headers(self._token_store.session_id)
        headers["Authorization"] = f"Bearer {access_token}"
        from energy_core.vehicles.mercedes.constants import widget_api_base

        url = f"{widget_api_base(self._region)}/v1/vehicle/{vin}/vehicleattributes"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 429:
                raise httpx.HTTPStatusError("rate limited", request=response.request, response=response)
            response.raise_for_status()
            return response.content

    async def _request(self, method: str, endpoint: str) -> Any:
        access_token = await self._token_store.get_valid_access_token()
        headers = self._app_version.webapi_headers(self._token_store.session_id)
        headers["Authorization"] = f"Bearer {access_token}"
        url = f"{rest_api_base(self._region)}{endpoint}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(method, url, headers=headers)
            if response.status_code == 429:
                raise httpx.HTTPStatusError("rate limited", request=response.request, response=response)
            response.raise_for_status()
            payload = response.json()
        if endpoint == "/v1/config" and isinstance(payload, dict):
            self._app_version.apply_config(payload)
        return payload
