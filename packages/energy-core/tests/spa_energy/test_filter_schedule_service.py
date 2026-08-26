"""Tests for filter schedule transactional updates."""

from unittest.mock import AsyncMock

import pytest

from energy_core.integrations.arctic_spa.models import ArcticSpaStatus
from energy_core.spa_energy.filter_policy import SpaFilterPolicy
from energy_core.spa_energy.filter_schedule_service import ArcticSpaFilterScheduleService


def _status(*, frequency: float = 4, duration: float = 2) -> ArcticSpaStatus:
    return ArcticSpaStatus(
        connected=True,
        temperature_c=38.0,
        setpoint_c=38.0,
        lights=None,
        pump1="low",
        pump2=None,
        pump3=None,
        pump4=None,
        pump5=None,
        filter_status="Idle",
        filter_frequency=frequency,
        filter_duration=duration,
        filter_suspension=False,
        blower1=None,
        blower2=None,
        errors=[],
        raw={},
    )


@pytest.mark.asyncio
async def test_apply_policy_skips_write_when_already_matching():
    policy = SpaFilterPolicy()
    service = ArcticSpaFilterScheduleService()
    control = AsyncMock()
    control.get_status = AsyncMock(return_value=_status(frequency=4, duration=2))

    result = await service.apply_policy(control, policy, dry_run=False, last_known_safe_json=None)

    assert result.success is True
    assert result.verified is True
    control.ensure_safety_floor.assert_not_called()


@pytest.mark.asyncio
async def test_apply_policy_dry_run_does_not_write():
    policy = SpaFilterPolicy()
    service = ArcticSpaFilterScheduleService()
    control = AsyncMock()
    control.get_status = AsyncMock(return_value=_status(frequency=1, duration=2))

    result = await service.apply_policy(control, policy, dry_run=True, last_known_safe_json=None)

    assert result.success is True
    assert result.verified is False
    control.ensure_safety_floor.assert_not_called()


@pytest.mark.asyncio
async def test_apply_policy_restores_baseline_on_read_back_mismatch():
    policy = SpaFilterPolicy()
    service = ArcticSpaFilterScheduleService()
    control = AsyncMock()
    control.get_status = AsyncMock(
        side_effect=[
            _status(frequency=1, duration=2),
            _status(frequency=1, duration=2),
            _status(frequency=4, duration=2),
        ]
    )
    control.ensure_safety_floor = AsyncMock()

    safe_json = policy.to_safe_schedule_json()
    result = await service.apply_policy(control, policy, dry_run=False, last_known_safe_json=safe_json)

    assert result.success is False
    assert result.degraded is True
    assert control.ensure_safety_floor.call_count >= 2
