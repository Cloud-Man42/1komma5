"""Tests for Zaptec REST adapter control methods."""

from __future__ import annotations

import pytest

from energy_core.integrations.zaptec.adapter import ZaptecRestAdapter
from energy_core.integrations.zaptec.config import ZaptecConnectionInfo
from energy_core.integrations.zaptec.mock import ZaptecMockClient


def _adapter(*, installation_id: str | None = "install-1") -> ZaptecRestAdapter:
    client = ZaptecMockClient(charger_id="charger-1", installation_id=installation_id)
    connection = ZaptecConnectionInfo(
        charger_id="charger-1",
        installation_id=installation_id,
        username_configured=True,
        password_configured=True,
        mock=True,
        ready=False,
        notes=(),
    )
    return ZaptecRestAdapter(
        manufacturer_id="zaptec",
        model_id="go",
        client=client,
        charger_id="charger-1",
        installation_id=installation_id,
        connection_info=connection,
    )


@pytest.mark.asyncio
async def test_zaptec_adapter_start_and_stop_charging():
    adapter = _adapter()
    await adapter.start_charging()
    status = await adapter.get_status()
    assert status.charging is True
    await adapter.stop_charging()
    status = await adapter.get_status()
    assert status.charging is False


@pytest.mark.asyncio
async def test_zaptec_adapter_set_max_current_updates_mock_state():
    adapter = _adapter()
    await adapter.start_charging()
    await adapter.set_max_current(10.0)
    current = await adapter.get_actual_current()
    assert current == 10.0


@pytest.mark.asyncio
async def test_zaptec_adapter_set_max_current_requires_installation_id():
    adapter = _adapter(installation_id=None)
    with pytest.raises(ValueError, match="installation ID"):
        await adapter.set_max_current(8.0)
