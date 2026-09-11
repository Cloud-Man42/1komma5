"""Control lease semantics (F-13)."""



from __future__ import annotations



import pytest



from energy_core.config import Settings

from energy_core.platform.modules.brokers.device_control_broker import DeviceControlBroker





@pytest.mark.asyncio

async def test_command_denied_without_lease():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = DeviceControlBroker(settings)

    broker.synthetic.register_device(site_id=1, device_id="dev-1")

    with pytest.raises(PermissionError, match="AcquireControlLease"):

        await broker.command(

            runtime_instance_id="runtime-a",

            module_id="mod-a",

            site_id=1,

            capability="device.control",

            command="set_power",

            params={"device_id": "dev-1", "site_id": 1, "power_w": 1000},

            permissions=("device.control",),

        )





@pytest.mark.asyncio

async def test_acquire_then_command():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = DeviceControlBroker(settings)

    broker.synthetic.register_device(site_id=1, device_id="dev-1")

    await broker.acquire_lease(

        runtime_instance_id="runtime-a",

        module_id="mod-a",

        site_id=1,

        capability="device.control",

        params={"device_id": "dev-1", "site_id": 1},

        permissions=("device.control",),

    )

    result = await broker.command(

        runtime_instance_id="runtime-a",

        module_id="mod-a",

        site_id=1,

        capability="device.control",

        command="set_power",

        params={"device_id": "dev-1", "site_id": 1, "power_w": 2000},

        permissions=("device.control",),

    )

    assert result["ok"] is True





@pytest.mark.asyncio

async def test_expired_lease_requires_explicit_reacquire():

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

    with pytest.raises(PermissionError, match="AcquireControlLease"):

        await broker.command(

            runtime_instance_id="runtime-a",

            module_id="mod-a",

            site_id=1,

            capability="device.control",

            command="set_power",

            params={"device_id": "dev-1", "site_id": 1, "power_w": 1000},

            permissions=("device.control",),

        )





@pytest.mark.asyncio

async def test_renew_requires_active_lease():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = DeviceControlBroker(settings)

    with pytest.raises(PermissionError, match="no active lease"):

        await broker.renew_lease(

            runtime_instance_id="runtime-a",

            site_id=1,

            capability="device.control",

            params={"device_id": "dev-1"},

            permissions=("device.control",),

        )


