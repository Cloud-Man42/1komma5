"""Tests for capability clamping helper."""

from unittest.mock import AsyncMock

import pytest

from energy_core.charging.config import ChargingConfig
from energy_core.charging.engine import _clamp_config_to_capabilities
from energy_core.chargers.capabilities import ChargerCapabilities


@pytest.mark.asyncio
async def test_clamp_leaves_config_when_capabilities_unavailable():
    adapter = AsyncMock()
    adapter.get_capabilities.side_effect = RuntimeError("offline")
    config = ChargingConfig(max_current_a=32.0, min_current_a=6.0, phases=3)
    clamped = await _clamp_config_to_capabilities(config, adapter)
    assert clamped.max_current_a == 32.0
