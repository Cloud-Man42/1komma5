"""Heartbeat-backed energy provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from energy_core.energy.builder import build_energy_state
from energy_core.energy.state import EnergyState
from energy_core.heartbeat_client import HeartbeatClient


class HeartbeatEnergyProvider:
    """Fetch and normalize energy state from 1KOMMA5 Heartbeat."""

    def __init__(
        self,
        client: HeartbeatClient,
        *,
        system_id: str,
        ev_id: str | None = None,
    ) -> None:
        self._client = client
        self._system_id = system_id
        self._ev_id = ev_id

    async def get_energy_state(self, *, now: datetime | None = None) -> EnergyState:
        now = now or datetime.now(UTC)
        from_iso = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        to_iso = (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z")

        live_overview = await self._client.fetch_live_overview(self._system_id)
        ems = await self._client.fetch_ems_settings(self._system_id)
        market_prices = await self._client.fetch_market_prices(
            self._system_id,
            from_iso=from_iso,
            to_iso=to_iso,
        )
        optimizations = await self._client.fetch_optimizations(
            self._system_id,
            from_iso=from_iso,
            to_iso=to_iso,
        )
        ev: dict[str, Any] | None = None
        if self._ev_id:
            ev = await self._client.fetch_ev_by_id(self._system_id, self._ev_id)

        return build_energy_state(
            live_overview=live_overview,
            ev=ev,
            ems=ems,
            optimizations=optimizations,
            market_prices=market_prices,
            now=now,
        )
