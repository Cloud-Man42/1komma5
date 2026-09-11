"""Safe-state and lease expiry tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.brokers.device_control_broker import DeviceControlBroker


@pytest.mark.asyncio
async def test_runtime_revoke_resets_synthetic_device_power():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = DeviceControlBroker(settings)
    broker.synthetic.register_device(site_id=1, device_id="dev-1", safe_default_power_w=0.0)
    broker.grant_lease(runtime_instance_id="runtime-a", site_id=1, device_id="dev-1", capability="device.control")
    await broker.command(
        runtime_instance_id="runtime-a",
        module_id="mod-a",
        site_id=1,
        capability="device.control",
        command="set_power",
        params={"device_id": "dev-1", "site_id": 1, "power_w": 5000},
        permissions=("device.control",),
    )
    device = broker.synthetic.get(1, "dev-1")
    assert device is not None
    assert device.power_w == 5000
    broker.revoke_runtime("runtime-a")
    assert device.power_w == 0.0
    assert device.owner_runtime_id is None


@pytest.mark.asyncio
async def test_command_after_revoke_requires_new_lease():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = DeviceControlBroker(settings)
    broker.synthetic.register_device(site_id=1, device_id="dev-1")
    broker.grant_lease(
        runtime_instance_id="runtime-a",
        site_id=1,
        device_id="dev-1",
        capability="device.control",
        ttl_seconds=0.01,
    )
    import asyncio

    await asyncio.sleep(0.02)
    assert not broker.lease_valid(
        runtime_instance_id="runtime-a",
        site_id=1,
        device_id="dev-1",
        capability="device.control",
    )
