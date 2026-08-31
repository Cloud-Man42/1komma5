"""HTTP client for 1Komma5 HeartBeat API (energy + EV control)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from energy_core.heartbeat_connection import CLOUD_HOST, build_heartbeat_api_url, HeartbeatConnectionType

logger = logging.getLogger(__name__)

CHARGING_MODES = ("SMART_CHARGE", "PRICE_CHARGE", "QUICK_CHARGE", "SOLAR_CHARGE", "PAUSED")
TokenRefreshCallback = Callable[[], Awaitable[str]]

_breakers: dict[str, Any] = {}
_lkg_store: Any = None
_http_clients: dict[float, httpx.AsyncClient] = {}


def _breaker_for(api_url: str) -> Any:
    from energy_core.providers.resilience import CircuitBreaker

    if api_url not in _breakers:
        _breakers[api_url] = CircuitBreaker()
    return _breakers[api_url]


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
class HeartbeatCredentials:
    api_url: str
    api_token: str
    username: str = ""
    password: str = ""


@dataclass(frozen=True, slots=True)
class EvChargerLiveState:
    heartbeat_ev_id: str
    name: str
    manufacturer: str
    model: str
    charging_mode: str | None
    target_soc_pct: float | None
    manual_soc_pct: float | None
    departure_time: str | None
    power_w: float | None
    heartbeat_charger_id: str | None


class HeartbeatClient:
    def __init__(
        self,
        credentials: HeartbeatCredentials,
        timeout: float = 20.0,
        *,
        refresh_token: TokenRefreshCallback | None = None,
    ) -> None:
        self._credentials = credentials
        self._api_token = credentials.api_token
        self._timeout = timeout
        self._refresh_token = refresh_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._credentials.api_url.rstrip('/')}{path}"
        max_attempts = 3
        for attempt in range(max_attempts):
            token = self._api_token
            if not token:
                raise RuntimeError(
                    "HeartBeat Bearer-token saknas. Ange token eller e-post/lösenord i konfigurationen."
                )

            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            client = _http_client(self._timeout)
            response = await client.request(method, url, headers=headers, json=json)

            if response.status_code == 401 and attempt == 0 and self._refresh_token is not None:
                logger.info("HeartBeat token rejected, refreshing from credentials")
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

    async def _resilient_dict(
        self,
        key: str,
        fetch: Callable[[], Awaitable[Any]],
        *,
        max_age_seconds: float = 120.0,
    ) -> dict[str, Any]:
        from energy_core.providers.resilience import resilient_call

        async def call() -> dict[str, Any]:
            data = await fetch()
            if not isinstance(data, dict) or not data:
                raise RuntimeError(f"{key} returned empty payload")
            return data

        try:
            return await resilient_call(
                breaker=_breaker_for(self._credentials.api_url),
                lkg=_lkg(),
                key=key,
                call=call,
                max_age_seconds=max_age_seconds,
                should_cache=lambda payload: isinstance(payload, dict) and bool(payload),
            )
        except Exception:
            cached = _lkg().get(key, max_age_seconds=max_age_seconds)
            return cached if isinstance(cached, dict) else {}

    async def list_evs(self, system_id: str) -> list[dict[str, Any]]:
        key = f"evs:{system_id}"

        async def call() -> list[dict[str, Any]]:
            data = await self._request("GET", f"/v1/systems/{system_id}/devices/evs")
            return data if isinstance(data, list) else []

        from energy_core.providers.resilience import resilient_call

        try:
            return await resilient_call(
                breaker=_breaker_for(self._credentials.api_url),
                lkg=_lkg(),
                key=key,
                call=call,
                max_age_seconds=120.0,
                should_cache=lambda payload: isinstance(payload, list),
            )
        except Exception:
            cached = _lkg().get(key, max_age_seconds=120.0)
            return cached if isinstance(cached, list) else []

    async def list_wallboxes(self, system_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/v1/systems/{system_id}/devices/ev-chargers")
        return data if isinstance(data, list) else []

    async def list_charging_modes(self, system_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/v1/sites/{system_id}/assets/evs/displayed-ev-charging-modes")
        if isinstance(data, dict):
            return data.get("displayedEvChargingModes", [])
        return []

    async def fetch_live_ev_power(self, system_id: str) -> float | None:
        data = await self.fetch_live_overview(system_id)
        if not data:
            return None
        aggregated = data.get("evChargersAggregated") or {}
        power = aggregated.get("power")
        if isinstance(power, dict):
            return float(power.get("value", 0))
        if isinstance(power, (int, float)):
            return float(power)
        hero = data.get("liveHeroView") or {}
        aggregated = hero.get("evChargersAggregated") or {}
        power = aggregated.get("power")
        if isinstance(power, dict):
            return float(power.get("value", 0))
        if isinstance(power, (int, float)):
            return float(power)
        return None

    async def fetch_live_overview(self, system_id: str) -> dict[str, Any]:
        from energy_core.providers.resilience import resilient_call

        key = f"live-overview:{system_id}"

        async def call() -> dict[str, Any]:
            data = await self._request("GET", f"/v3/systems/{system_id}/live-overview")
            if not isinstance(data, dict) or not data:
                raise RuntimeError("HeartBeat live-overview returned empty payload")
            return data

        return await resilient_call(
            breaker=_breaker_for(self._credentials.api_url),
            lkg=_lkg(),
            key=key,
            call=call,
            max_age_seconds=120.0,
            should_cache=lambda payload: isinstance(payload, dict) and bool(payload),
        )

    async def fetch_ems_settings(self, system_id: str) -> dict[str, Any]:
        return await self._resilient_dict(
            f"ems-settings:{system_id}",
            lambda: self._request("GET", f"/v1/systems/{system_id}/ems/actions/get-settings"),
        )

    async def fetch_market_prices(
        self,
        system_id: str,
        *,
        from_iso: str,
        to_iso: str,
        resolution: str = "1h",
    ) -> dict[str, Any]:
        return await self._resilient_dict(
            f"market-prices:{system_id}:{from_iso}:{to_iso}:{resolution}",
            lambda: self._request(
                "GET",
                f"/v4/systems/{system_id}/charts/market-prices?from={from_iso}&to={to_iso}&resolution={resolution}",
            ),
            max_age_seconds=300.0,
        )

    async def fetch_heartbeat_prices(self, system_id: str) -> dict[str, Any]:
        """Contractual feed-in and heartbeat tariffs for the site."""
        return await self._resilient_dict(
            f"heartbeat-prices:{system_id}",
            lambda: self._request("GET", f"/v3/heartbeat-prices?siteId={system_id}"),
            max_age_seconds=3600.0,
        )

    async def fetch_optimizations(
        self,
        system_id: str,
        *,
        from_iso: str,
        to_iso: str,
    ) -> list[dict[str, Any]]:
        try:
            data = await self._request(
                "GET",
                f"/v1/heartbeat-ai/optimizations?systemId={system_id}&from={from_iso}&to={to_iso}",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {400, 403, 404}:
                logger.warning(
                    "HeartBeat optimizations unavailable for system %s (HTTP %s)",
                    system_id,
                    exc.response.status_code,
                )
                return []
            raise
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get("optimizations") or data.get("items") or data.get("data")
            return items if isinstance(items, list) else []
        return []

    async def fetch_ev_by_id(self, system_id: str, ev_id: str) -> dict[str, Any] | None:
        evs = await self.list_evs(system_id)
        for ev in evs:
            if str(ev.get("id")) == ev_id:
                return ev
        return None


def build_heartbeat_client(
    *,
    connection_type: str,
    host: str,
    port: int,
    use_tls: bool,
    api_path: str,
    api_token: str,
    username: str = "",
    password: str = "",
    refresh_token: TokenRefreshCallback | None = None,
) -> HeartbeatClient | None:
    if connection_type == HeartbeatConnectionType.MOCK.value:
        return None

    api_url = build_heartbeat_api_url(
        connection_type,
        host=host or (CLOUD_HOST if connection_type == HeartbeatConnectionType.CLOUD.value else ""),
        port=port,
        use_tls=use_tls,
        api_path=api_path,
    )
    if not api_url:
        return None

    return HeartbeatClient(
        HeartbeatCredentials(
            api_url=api_url,
            api_token=api_token,
            username=username,
            password=password,
        ),
        refresh_token=refresh_token,
    )


def map_ev_live_state(ev: dict[str, Any], power_w: float | None = None) -> EvChargerLiveState:
    profile = ev.get("profile") or {}
    charge_settings = ev.get("chargeSettings") or {}
    target_soc = charge_settings.get("targetSoc")
    manual_soc = ev.get("manualSoc")
    return EvChargerLiveState(
        heartbeat_ev_id=str(ev.get("id", "")),
        name=str(profile.get("name") or "EV"),
        manufacturer=str(profile.get("manufacturer") or ""),
        model=str(profile.get("model") or ""),
        charging_mode=charge_settings.get("chargingMode"),
        target_soc_pct=float(target_soc) * 100 if target_soc is not None else None,
        manual_soc_pct=float(manual_soc) * 100 if manual_soc is not None else None,
        departure_time=charge_settings.get("primaryScheduleDepartureTime"),
        power_w=power_w,
        heartbeat_charger_id=ev.get("assignedChargerId"),
    )
