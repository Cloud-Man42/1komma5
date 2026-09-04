"""Tests for Heartbeat control provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from energy_core.energy_control.heartbeat_provider import HeartbeatControlProvider
from energy_core.energy_control.types import ControlOutcome, ControlTarget
from energy_core.energy_optimizer.types import EnergyAction


@pytest.fixture
def session() -> AsyncMock:
    mock = AsyncMock()
    mock.scalar = AsyncMock(return_value=None)
    return mock


@pytest.mark.asyncio
async def test_heartbeat_provider_skips_battery_action(session: AsyncMock) -> None:
    site = MagicMock()
    site.external_system_id = "sys-1"
    session.scalar = AsyncMock(return_value=site)
    provider = HeartbeatControlProvider(session)

    result = await provider.apply_action(
        site_id=1,
        action=EnergyAction.STORE_IN_BATTERY,
        target=ControlTarget.BATTERY,
        dry_run=True,
    )

    assert result.outcome == ControlOutcome.SKIPPED
    assert result.provider == "heartbeat"


@pytest.mark.asyncio
async def test_heartbeat_provider_dry_run_ev_action(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    site.external_system_id = "sys-1"
    session.scalar = AsyncMock(return_value=site)

    mapping = MagicMock()
    mapping.heartbeat_ev_id = "ev-42"

    provider = HeartbeatControlProvider(session)
    with patch.object(provider._discovery, "list_mappings", AsyncMock(return_value=[mapping])):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.USE_NOW,
            target=ControlTarget.EV_CHARGER,
            dry_run=True,
        )

    assert result.outcome == ControlOutcome.PREVIEW
    assert result.payload["payload"]["chargeSettings"]["chargingMode"] == "QUICK_CHARGE"


@pytest.mark.asyncio
async def test_heartbeat_provider_falls_back_to_charger_ev_id(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    site.external_system_id = "sys-1"
    session.scalar = AsyncMock(return_value=site)

    charger = MagicMock()
    charger.heartbeat_ev_id = "ev-from-charger"

    provider = HeartbeatControlProvider(session)
    with (
        patch.object(provider._discovery, "list_mappings", AsyncMock(return_value=[])),
        patch(
            "energy_core.db.ev_charger_repo.EvChargerRepository",
            return_value=MagicMock(list_for_site=AsyncMock(return_value=[charger])),
        ),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.USE_NOW,
            target=ControlTarget.EV_CHARGER,
            dry_run=True,
        )

    assert result.outcome == ControlOutcome.PREVIEW
    assert result.payload["heartbeat_ev_id"] == "ev-from-charger"


@pytest.mark.asyncio
async def test_heartbeat_provider_rejects_when_write_disabled(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    site.external_system_id = "sys-1"
    session.scalar = AsyncMock(return_value=site)

    mapping = MagicMock()
    mapping.heartbeat_ev_id = "ev-42"
    mapping.confidence_pct = 95

    bridge_settings = MagicMock()
    bridge_settings.write_enabled = False
    bridge_settings.confidence_threshold_pct = 80

    provider = HeartbeatControlProvider(session)
    with (
        patch.object(provider._discovery, "list_mappings", AsyncMock(return_value=[mapping])),
        patch.object(
            provider._discovery,
            "get_or_create_bridge_settings",
            AsyncMock(return_value=bridge_settings),
        ),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.WAIT,
            target=ControlTarget.EV_CHARGER,
            dry_run=False,
        )

    assert result.outcome == ControlOutcome.REJECTED
