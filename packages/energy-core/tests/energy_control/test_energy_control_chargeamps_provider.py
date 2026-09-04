"""Tests for Charge Amps control provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from energy_core.charging.command_controller import CommandApplyResult
from energy_core.energy_control.chargeamps_provider import ChargeAmpsControlProvider
from energy_core.energy_control.types import ControlOutcome, ControlTarget
from energy_core.energy_optimizer.types import EnergyAction


@pytest.fixture
def session() -> AsyncMock:
    mock = AsyncMock()
    mock.scalar = AsyncMock(return_value=None)
    return mock


def _charger(*, bridge_enabled: bool = True, charger_id: int = 7) -> MagicMock:
    charger = MagicMock()
    charger.id = charger_id
    charger.name = "Halo"
    charger.bridge_enabled = bridge_enabled
    charger.max_current_a = 16.0
    charger.charging_mode = "SOLAR"
    return charger


@pytest.mark.asyncio
async def test_chargeamps_provider_skips_battery_action(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)
    provider = ChargeAmpsControlProvider(session)

    result = await provider.apply_action(
        site_id=1,
        action=EnergyAction.STORE_IN_BATTERY,
        target=ControlTarget.BATTERY,
        dry_run=True,
    )

    assert result.outcome == ControlOutcome.SKIPPED
    assert result.provider == "chargeamps"


@pytest.mark.asyncio
async def test_chargeamps_provider_dry_run_use_now(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)

    provider = ChargeAmpsControlProvider(session)
    with patch.object(
        provider._chargers,
        "list_for_site",
        AsyncMock(return_value=[_charger()]),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.USE_NOW,
            target=ControlTarget.EV_CHARGER,
            dry_run=True,
        )

    assert result.outcome == ControlOutcome.PREVIEW
    assert result.payload["charging_mode"] == "QUICK_CHARGE"
    assert result.payload["charger_id"] == 7


@pytest.mark.asyncio
async def test_chargeamps_provider_rejects_without_bridge_charger(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)

    provider = ChargeAmpsControlProvider(session)
    with patch.object(provider._chargers, "list_for_site", AsyncMock(return_value=[])):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.WAIT,
            target=ControlTarget.EV_CHARGER,
            dry_run=True,
        )

    assert result.outcome == ControlOutcome.REJECTED


@pytest.mark.asyncio
async def test_chargeamps_provider_rejects_when_bridge_disabled(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)

    provider = ChargeAmpsControlProvider(session)
    with patch.object(
        provider._chargers,
        "list_for_site",
        AsyncMock(return_value=[_charger(bridge_enabled=False)]),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.USE_NOW,
            target=ControlTarget.EV_CHARGER,
            dry_run=False,
        )

    assert result.outcome == ControlOutcome.REJECTED


@pytest.mark.asyncio
async def test_chargeamps_provider_applies_use_now(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)
    charger = _charger()

    provider = ChargeAmpsControlProvider(session)
    apply_result = CommandApplyResult(
        applied=True,
        applied_current_a=16.0,
        reason="energy_control USE_NOW",
        charger_status=None,
        error_code=None,
    )

    update_mock = AsyncMock(return_value=charger)
    with (
        patch.object(provider._chargers, "list_for_site", AsyncMock(return_value=[charger])),
        patch.object(provider._chargers, "update", update_mock),
        patch(
            "energy_core.energy_control.chargeamps_provider.ChargingCommandController.apply",
            AsyncMock(return_value=apply_result),
        ),
        patch("energy_core.energy_control.chargeamps_provider.ChargerAdapterFactory.from_charger_model"),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.USE_NOW,
            target=ControlTarget.EV_CHARGER,
            dry_run=False,
        )

    assert result.outcome == ControlOutcome.APPLIED
    assert result.payload["applied_current_a"] == 16.0
    update_mock.assert_awaited_once_with(charger, charging_mode="QUICK_CHARGE")


@pytest.mark.asyncio
async def test_chargeamps_provider_apply_failure_returns_failed(session: AsyncMock) -> None:
    site = MagicMock()
    site.id = 1
    session.scalar = AsyncMock(return_value=site)
    charger = _charger()

    provider = ChargeAmpsControlProvider(session)
    apply_result = CommandApplyResult(
        applied=False,
        applied_current_a=0.0,
        reason="charger_disconnected",
        charger_status=None,
        error_code="CHARGER_DISCONNECTED",
    )

    with (
        patch.object(provider._chargers, "list_for_site", AsyncMock(return_value=[charger])),
        patch.object(provider._chargers, "update", AsyncMock(return_value=charger)),
        patch(
            "energy_core.energy_control.chargeamps_provider.ChargingCommandController.apply",
            AsyncMock(return_value=apply_result),
        ),
        patch("energy_core.energy_control.chargeamps_provider.ChargerAdapterFactory.from_charger_model"),
    ):
        result = await provider.apply_action(
            site_id=1,
            action=EnergyAction.WAIT,
            target=ControlTarget.EV_CHARGER,
            dry_run=False,
        )

    assert result.outcome == ControlOutcome.FAILED
    assert result.payload["error_code"] == "CHARGER_DISCONNECTED"
