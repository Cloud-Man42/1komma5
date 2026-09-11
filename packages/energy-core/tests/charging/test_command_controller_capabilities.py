"""Tests for ChargingCommandController capability guards."""

from unittest.mock import AsyncMock

import pytest

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.framework.models import ChargerCapabilities
from energy_core.charging.anti_flapping import AntiFlappingConfig, AntiFlappingState
from energy_core.charging.command_controller import ChargingCommandController
from energy_core.charging.models import ChargingDecision


@pytest.mark.asyncio
async def test_controller_rejects_set_current_when_unsupported():
    adapter = AsyncMock()
    adapter.get_capabilities.return_value = ChargerCapabilities(
        supports_current_control=False,
        supports_remote_start_stop=True,
    )
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(
        ChargingDecision(
            requested_current_a=12.0,
            applied_current_a=12.0,
            requested_power_w=None,
            action="set_current",
            reason="test",
            policy_mode="smart",
        )
    )
    assert result.applied is False
    assert result.error_code == "CAPABILITY_SET_CURRENT_UNSUPPORTED"
    adapter.set_current.assert_not_awaited()
