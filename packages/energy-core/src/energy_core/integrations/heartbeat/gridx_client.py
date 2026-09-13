"""HTTP client for GridX-backed 1KOMMA5 installations (api.gridx.de)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from energy_core.integrations.heartbeat.gridx_defaults import GRIDX_API_HOST

logger = logging.getLogger(__name__)

TokenRefreshCallback = Callable[[], Awaitable[str]]

_breakers: dict[str, Any] = {}
_lkg_store: Any = None
_http_clients: dict[float, httpx.AsyncClient] = {}


def _breaker_for(api_url: str, *, account_id: int | None = None) -> Any:
    from energy_core.providers.resilience import CircuitBreaker

    key = f"acct:{account_id}:{api_url}" if account_id is not None else api_url
    if key not in _breakers:
        _breakers[key] = CircuitBreaker()
    return _breakers[key]


def _lkg() -> Any:
    global _lkg_store
    if _lkg_store is None:
        from energy_core.providers.resilience import LastKnownGoodStore

        _lkg_store = LastKnownGoodStore()
    return _lkg_store


def _http_client(timeout: float) -> httpx.AsyncClient:
    client = _http_clients.get(timeout)
    if client is None:
        client = httpx.AsyncClient(timeout=timeout)
        _http_clients[timeout] = client
    return client


@dataclass(frozen=True, slots=True)
class GridXCredentials:
    api_url: str
    api_token: str


class GridXClient:
    """GridX REST client — same fetch_live_overview surface as HeartbeatClient."""

    def __init__(
        self,
        credentials: GridXCredentials,
        timeout: float = 20.0,
        *,
        refresh_token: TokenRefreshCallback | None = None,
        account_id: int | None = None,
    ) -> None:
        self._credentials = credentials
        self._api_token = credentials.api_token
        self._timeout = timeout
        self._refresh_token = refresh_token
        self._account_id = account_id
        self._cache_prefix = f"acct:{account_id}:" if account_id is not None else ""

    def _cache_key(self, key: str) -> str:
        return f"{self._cache_prefix}{key}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._credentials.api_url.rstrip('/')}{path}"
        max_attempts = 3
        for attempt in range(max_attempts):
            token = self._api_token
            if not token:
                raise RuntimeError("GridX Bearer-token saknas. Ange e-post/lösenord i konfigurationen.")

            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            client = _http_client(self._timeout)
            response = await client.request(method, url, headers=headers, params=params, json=json)

            if response.status_code == 401 and attempt == 0 and self._refresh_token is not None:
                logger.info("GridX token rejected, refreshing from credentials")
                self._api_token = await self._refresh_token()
                continue

            if response.status_code >= 500 and attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                continue

            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        return None

    async def fetch_account(self) -> dict[str, Any]:
        data = await self._request("GET", "/account")
        return data if isinstance(data, dict) else {}

    async def fetch_system(self, system_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/systems/{system_id}")
        return data if isinstance(data, dict) else {}

    async def fetch_live_overview(self, system_id: str) -> dict[str, Any]:
        from energy_core.providers.resilience import resilient_call

        key = f"gridx-live:{system_id}"

        async def call() -> dict[str, Any]:
            data = await self._request("GET", f"/systems/{system_id}/live")
            if not isinstance(data, dict) or not data:
                raise RuntimeError("GridX live returned empty payload")
            return data

        return await resilient_call(
            breaker=_breaker_for(self._credentials.api_url, account_id=self._account_id),
            lkg=_lkg(),
            key=self._cache_key(key),
            call=call,
            max_age_seconds=120.0,
            should_cache=lambda payload: isinstance(payload, dict) and bool(payload),
        )

    async def fetch_historical(self, system_id: str, *, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", f"/systems/{system_id}/historical", params=params)

    async def fetch_tariff(self, system_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/systems/{system_id}/tariff")
        return data if isinstance(data, dict) else {}

    async def fetch_tariff_prices(
        self,
        system_id: str,
        *,
        from_iso: str | None = None,
        to_iso: str | None = None,
        resolution: str = "15m",
    ) -> Any:
        params: dict[str, Any] | None = None
        if from_iso and to_iso:
            params = {"interval": f"{from_iso}/{to_iso}"}
            if resolution == "15m":
                params["step"] = "15m"
        return await self._request("GET", f"/systems/{system_id}/tariff/prices", params=params)

    async def fetch_market_prices(
        self,
        system_id: str,
        *,
        from_iso: str = "",
        to_iso: str = "",
        resolution: str = "15m",
        **kwargs: Any,
    ) -> Any:
        """Price-engine compatibility alias for GridX tariff end-prices."""
        data = await self.fetch_tariff_prices(
            system_id,
            from_iso=from_iso or None,
            to_iso=to_iso or None,
            resolution=resolution,
        )
        return data if isinstance(data, dict) else {}

    async def fetch_gateway_appliances(self, gateway_id: str, *, list_all: bool = True) -> list[dict[str, Any]]:
        params = {"listAll": "true"} if list_all else None
        data = await self._request("GET", f"/gateways/{gateway_id}/appliances", params=params)
        return data if isinstance(data, list) else []

    async def fetch_gateway_network(self, gateway_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/gateways/{gateway_id}/network")
        return data if isinstance(data, dict) else {}

    async def fetch_gateway_gsp(self, gateway_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/gateways/{gateway_id}/gsp")
        return data if isinstance(data, dict) else {}

    async def fetch_gateway_gsp_assets(self, gateway_id: str) -> Any:
        return await self._request("GET", f"/gateways/{gateway_id}/gsp/assets")


def build_gridx_client(
    *,
    host: str = "",
    port: int = 443,
    use_tls: bool = True,
    api_token: str,
    refresh_token: TokenRefreshCallback | None = None,
    account_id: int | None = None,
) -> GridXClient:
    host = host.strip() or GRIDX_API_HOST
    scheme = "https" if use_tls else "http"
    default_port = 443 if use_tls else 80
    port_suffix = "" if port in (0, default_port) else f":{port}"
    if host.startswith("http://") or host.startswith("https://"):
        api_url = host.rstrip("/")
    else:
        api_url = f"{scheme}://{host}{port_suffix}"

    return GridXClient(
        GridXCredentials(api_url=api_url, api_token=api_token),
        refresh_token=refresh_token,
        account_id=account_id,
    )
