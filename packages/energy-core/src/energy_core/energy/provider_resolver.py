"""Resolve energy state providers via capability registry (vendor-neutral entry point)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.energy.heartbeat_provider import HeartbeatEnergyProvider
from energy_core.energy.client_access import open_heartbeat_client
from energy_core.energy.optimizations import parse_active_optimizations
from energy_core.energy.state import EnergyState
from energy_core.platform.capabilities.registry import default_capability_registry
from energy_core.platform.capabilities.types import Capability


class IEnergyStateProvider(Protocol):
    async def get_energy_state(self, *, now=None) -> EnergyState: ...

    async def get_active_optimizations(self, *, now: datetime | None = None) -> tuple[str, ...]: ...


class _HeartbeatEnergyProviderAdapter:
    """Wraps HeartbeatEnergyProvider with optimization contract."""

    def __init__(self, inner: HeartbeatEnergyProvider) -> None:
        self._inner = inner

    async def get_energy_state(self, *, now=None) -> EnergyState:
        return await self._inner.get_energy_state(now=now)

    async def get_active_optimizations(self, *, now: datetime | None = None) -> tuple[str, ...]:
        now = now or datetime.now(UTC)
        from_iso = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        to_iso = (now + timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        items = await self._inner._client.fetch_optimizations(  # noqa: SLF001
            self._inner._system_id,
            from_iso=from_iso,
            to_iso=to_iso,
        )
        return parse_active_optimizations(items, now=now)


async def resolve_energy_state_provider(
    session: AsyncSession,
    site: SiteModel,
    *,
    ev_id: str | None = None,
) -> IEnergyStateProvider | None:
    """Return an energy state provider for the site based on registered capabilities."""
    providers = default_capability_registry.providers_for(
        site.id,
        Capability.ENERGY_READ_GRID_POWER,
    )
    if not providers:
        client = await open_heartbeat_client(session)
        if client is None or site.external_system_id is None:
            return None
        return _HeartbeatEnergyProviderAdapter(
            HeartbeatEnergyProvider(
                client,
                system_id=site.external_system_id,
                ev_id=ev_id,
            )
        )

    module_id = providers[0].module_id
    if module_id == "integration.heartbeat":
        client = await open_heartbeat_client(session)
        if client is None or site.external_system_id is None:
            return None
        return _HeartbeatEnergyProviderAdapter(
            HeartbeatEnergyProvider(
                client,
                system_id=site.external_system_id,
                ev_id=ev_id,
            )
        )
    return None
