"""IMeterReader contract tests."""

import pytest

from energy_core.contracts.devices.meter import IMeterReader
from energy_core.integrations.chargeamps.meter_adapter import ChargeAmpsMeterAdapter


@pytest.mark.asyncio
async def test_chargeamps_meter_adapter_satisfies_imeter_reader():
    adapter = ChargeAmpsMeterAdapter.build("mock-charger", api_key="")
    assert isinstance(adapter, IMeterReader)
    snapshot = await adapter.get_snapshot()
    assert snapshot.energy_source == "unavailable"
