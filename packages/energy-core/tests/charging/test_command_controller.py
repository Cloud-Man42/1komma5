"""Tests for ChargingCommandController."""

from unittest.mock import AsyncMock

import pytest

from energy_core.chargers.base import ChargerStatus
from energy_core.chargers.errors import ChargerApiError
from energy_core.charging.anti_flapping import AntiFlappingConfig, AntiFlappingState
from energy_core.charging.command_controller import ChargingCommandController
from energy_core.charging.models import ChargingDecision


def _decision(current: float, action: str = "set_current", reason: str = "test") -> ChargingDecision:
    return ChargingDecision(
        requested_current_a=current,
        applied_current_a=current,
        requested_power_w=None,
        action=action,
        reason=reason,
        policy_mode="smart",
    )


@pytest.mark.asyncio
async def test_controller_skips_pause_decision_but_refreshes_status():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=False,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(last_applied_current_a=8.0),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(0.0, action="pause", reason="wait"))
    assert result.applied is False
    assert result.applied_current_a == 8.0
    assert result.charger_status is not None
    assert result.charger_status.vehicle_connected is False
    adapter.get_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_controller_refreshes_status_when_anti_flapping_blocks():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=False,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(last_applied_current_a=0.0, last_change_at=None),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=3600, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(0.0, action="stop", reason="smart_wait_cheaper"))
    assert result.applied is False
    assert result.charger_status is not None
    assert result.charger_status.vehicle_connected is False


@pytest.mark.asyncio
async def test_controller_reasserts_stop_when_saved_zero_but_charger_is_charging():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=True,
        current_limit_a=16.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=0.0,
            last_command_current_a=0.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=3600, current_hysteresis_a=1),
    )

    result = await controller.apply(_decision(0.0, action="stop", reason="smart_wait_cheaper"))

    assert result.applied is True
    assert result.applied_current_a == 0.0
    adapter.stop_charging.assert_awaited_once()


@pytest.mark.asyncio
async def test_controller_reasserts_current_when_charger_drifted_from_saved_state():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=12.0,
            last_command_current_a=12.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=3600, current_hysteresis_a=1),
    )

    result = await controller.apply(_decision(12.0))

    assert result.applied is True
    adapter.set_current.assert_awaited_once_with(12.0)
    adapter.start_charging.assert_awaited_once()


@pytest.mark.asyncio
async def test_controller_starts_idle_charger_whose_limit_already_matches():
    """The live stuck-session shape: limit already 16 A, but the charger is idle.

    Nothing about the current needs changing, so only the missing start command
    separates this from a healthy session. The limit matching the saved state
    must not be read as "already applied".
    """
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=False,
        current_limit_a=16.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=16.0,
            last_command_current_a=16.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=3600, current_hysteresis_a=1),
    )

    result = await controller.apply(_decision(16.0))

    assert result.applied is True
    adapter.set_current.assert_awaited_once_with(16.0)
    adapter.start_charging.assert_awaited_once()


@pytest.mark.asyncio
async def test_controller_reports_offline_charger():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=False,
        vehicle_connected=False,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is False
    assert result.error_code == "CHARGER_OFFLINE"
    assert result.reason == "charger_offline"


@pytest.mark.asyncio
async def test_controller_skips_without_vehicle():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=False,
        charging=False,
        current_limit_a=0.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is False
    assert result.reason == "no_vehicle_connected"


@pytest.mark.asyncio
async def test_controller_applies_current_and_starts_charging():
    adapter = AsyncMock()
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
    result = await controller.apply(_decision(12.0))
    assert result.applied is True
    assert result.applied_current_a == 12.0
    adapter.set_current.assert_awaited_once_with(12.0)
    adapter.start_charging.assert_awaited_once()


@pytest.mark.asyncio
async def test_controller_does_not_chase_actual_when_already_requested():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=True,
        current_limit_a=12.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=12.0,
            last_command_current_a=12.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is False
    assert result.reason == "already_requested"
    adapter.set_current.assert_not_awaited()


@pytest.mark.asyncio
async def test_controller_skips_write_when_requested_12_actual_7():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=True,
        current_limit_a=7.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=12.0,
            last_command_current_a=12.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is False
    assert result.reason == "already_requested"
    adapter.set_current.assert_not_awaited()


@pytest.mark.asyncio
async def test_controller_writes_once_on_real_target_change():
    adapter = AsyncMock()
    adapter.get_status.return_value = ChargerStatus(
        connected=True,
        vehicle_connected=True,
        charging=True,
        current_limit_a=10.0,
    )
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(
            last_applied_current_a=10.0,
            last_command_current_a=10.0,
        ),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is True
    adapter.set_current.assert_awaited_once_with(12.0)


@pytest.mark.asyncio
async def test_controller_handles_api_error():
    adapter = AsyncMock()
    adapter.get_status.side_effect = ChargerApiError("RATE_LIMITED", "Too many requests")
    controller = ChargingCommandController(
        adapter,
        anti_flapping=AntiFlappingState(last_applied_current_a=6.0),
        anti_config=AntiFlappingConfig(min_change_interval_seconds=0, current_hysteresis_a=0),
    )
    result = await controller.apply(_decision(12.0))
    assert result.applied is False
    assert result.error_code == "RATE_LIMITED"
    assert result.applied_current_a == 6.0
