"""Mercedes REST API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from energy_core.vehicles.mercedes.api_client import MercedesApiClient
from energy_core.vehicles.mercedes.auth.app_version import MercedesAppVersionManager
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenStore
from energy_core.vehicles.mercedes.constants import rest_api_base, widget_api_base

logger = logging.getLogger(__name__)


class MercedesRestClient:
    def __init__(
        self,
        *,
        region: str,
        token_store: MercedesTokenStore,
        app_version: MercedesAppVersionManager,
        timeout: float = 30.0,
        api_client: MercedesApiClient | None = None,
    ) -> None:
        self._region = region
        self._token_store = token_store
        self._app_version = app_version
        self._timeout = timeout
        self._api = api_client or MercedesApiClient(
            token_store=token_store,
            request_headers=lambda: self._app_version.webapi_headers(token_store.session_id),
            base_url=rest_api_base(region),
            timeout=timeout,
        )

    @property
    def api_client(self) -> MercedesApiClient:
        return self._api

    async def get_config(self) -> dict[str, Any]:
        payload = await self._api.get_json("/v1/config")
        if isinstance(payload, dict):
            self._app_version.apply_config(payload)
        return payload if isinstance(payload, dict) else {}

    async def list_vehicles(self) -> list[dict[str, Any]]:
        vehicles: list[dict[str, Any]] = []
        try:
            vehicles = self._extract_vehicle_list(await self._api.get_json("/v2/vehicles"))
        except httpx.HTTPStatusError:
            raise
        except Exception as exc:
            if "404" in str(exc) or "405" in str(exc):
                logger.info("Mercedes /v2/vehicles unavailable, falling back to masterdata")
            else:
                raise
        if vehicles:
            return vehicles
        masterdata = await self._api.get_json("/v1/vehicle/self/masterdata")
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
        payload = await self._api.get_json(f"/v1/vehicle/{vin}/capabilities")
        return payload if isinstance(payload, dict) else {}

    async def get_command_capabilities(self, vin: str) -> dict[str, Any]:
        payload = await self._api.get_json(f"/v1/vehicle/{vin}/capabilities/commands")
        return payload if isinstance(payload, dict) else {}

    async def get_vehicle_attributes(self, vin: str) -> bytes:
        headers = dict(self._app_version.webapi_headers(self._token_store.session_id))
        headers["OUTPUT-FORMAT"] = "PROTO"
        url = f"{widget_api_base(self._region)}/v1/vehicle/{vin}/vehicleattributes"
        content = await self._api.get_bytes(url, extra_headers=headers)
        return content if isinstance(content, bytes) else bytes(content)
