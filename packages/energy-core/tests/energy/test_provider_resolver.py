"""Tests for vendor-neutral energy provider resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.energy.provider_resolver import resolve_energy_state_provider
from energy_core.platform.capabilities.registry import default_capability_registry
from energy_core.platform.capabilities.types import Capability


@pytest.mark.asyncio
async def test_resolve_energy_state_provider_via_capability_registry() -> None:
    session = AsyncMock()
    site = MagicMock()
    site.id = 1
    site.external_system_id = "sys-1"

    default_capability_registry.register_provider(
        site_id=1,
        module_id="integration.heartbeat",
        capability=Capability.ENERGY_READ_GRID_POWER,
    )
    try:
        mock_client = MagicMock()
        with patch(
            "energy_core.energy.provider_resolver.open_heartbeat_client",
            AsyncMock(return_value=mock_client),
        ):
            provider = await resolve_energy_state_provider(session, site)
        assert provider is not None
    finally:
        default_capability_registry.clear_site(1)


@pytest.mark.asyncio
async def test_resolve_energy_state_provider_none_without_client() -> None:
    session = AsyncMock()
    site = MagicMock()
    site.id = 2
    site.external_system_id = None

    default_capability_registry.clear_site(2)
    with patch(
        "energy_core.energy.provider_resolver.open_heartbeat_client",
        AsyncMock(return_value=None),
    ):
        provider = await resolve_energy_state_provider(session, site)
    assert provider is None
