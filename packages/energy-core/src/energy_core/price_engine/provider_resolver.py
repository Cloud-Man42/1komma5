"""Resolve price providers via capability registry."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import SiteModel
from energy_core.platform.capabilities.registry import default_capability_registry
from energy_core.platform.capabilities.types import Capability
from energy_core.price_engine.providers.registry import build_heartbeat_providers


class PriceProviderBundle(Protocol):
    market: object
    export: object


async def resolve_price_providers(
    session: AsyncSession,
    site: SiteModel,
) -> PriceProviderBundle | None:
    """Return price providers for a site based on registered capabilities."""
    from energy_core.energy.client_access import open_heartbeat_client

    providers = default_capability_registry.providers_for(
        site.id,
        Capability.PRICE_READ_FORECAST,
    )
    if not providers and site.external_system_id is None:
        return None
    module_id = providers[0].module_id if providers else "integration.heartbeat"
    if module_id in {"integration.heartbeat", "feature.price-engine"}:
        client = await open_heartbeat_client(session)
        if client is None:
            return None
        return build_heartbeat_providers(client, site)
    return None
