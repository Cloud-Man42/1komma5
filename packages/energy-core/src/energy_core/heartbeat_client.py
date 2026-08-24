"""HTTP client for 1Komma5 HeartBeat API (energy + EV control)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from energy_core.heartbeat_connection import CLOUD_HOST, build_heartbeat_api_url, HeartbeatConnectionType

logger = logging.getLogger(__name__)

CHARGING_MODES = ("SMART_CHARGE", "PRICE_CHARGE", "QUICK_CHARGE", "SOLAR_CHARGE", "PAUSED")
TokenRefreshCallback = Callable[[], Awaitable[str]]


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
        for attempt in range(2):
            token = self._api_token
            if not token:
                raise RuntimeError(
                    "HeartBeat Bearer-token saknas. Ange token eller e-post/lösenord i konfigurationen."
                )

            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(method, url, headers=headers, json=json)

            if response.status_code == 401 and attempt == 0 and self._refresh_token is not None:
                logger.info("HeartBeat token rejected, refreshing from credentials")
                self._api_token = await self._refresh_token()
                continue

            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        return None

    async def list_evs(self, system_id: str) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/v1/systems/{system_id}/devices/evs")
        return data if isinstance(data, list) else []

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
        data = await self._request("GET", f"/v3/systems/{system_id}/live-overview")
        return data if isinstance(data, dict) else {}

    async def fetch_ems_settings(self, system_id: str) -> dict[str, Any]:
        data = await self._request("GET", f"/v1/systems/{system_id}/ems/actions/get-settings")
        return data if isinstance(data, dict) else {}

    async def fetch_market_prices(
        self,
        system_id: str,
        *,
        from_iso: str,
        to_iso: str,
        resolution: str = "1h",
    ) -> dict[str, Any]:
        data = await self._request(
            "GET",
            f"/v4/systems/{system_id}/charts/market-prices?from={from_iso}&to={to_iso}&resolution={resolution}",
        )
        return data if isinstance(data, dict) else {}

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
