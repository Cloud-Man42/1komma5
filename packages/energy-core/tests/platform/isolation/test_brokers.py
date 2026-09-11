"""Broker security tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.brokers.device_control_broker import DeviceControlBroker
from energy_core.platform.modules.brokers.secret_broker import SecretBroker


@pytest.mark.asyncio
async def test_secret_broker_denies_cross_module():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = SecretBroker(settings)
    broker.register_secret(module_id="mod-a", site_id=1, secret_ref="secret-a", value="value-a")
    with pytest.raises(PermissionError):
        await broker.get_secret(
            runtime_instance_id="r1",
            module_id="mod-b",
            site_id=1,
            secret_ref="secret-a",
            permissions=("secrets.read_own",),
        )


@pytest.mark.asyncio
async def test_device_broker_cross_site_denied():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = DeviceControlBroker(settings)
    broker.synthetic.register_device(site_id=1, device_id="dev-1")
    with pytest.raises(PermissionError):
        await broker.command(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            capability="device.control",
            command="set_power",
            params={"device_id": "dev-1", "site_id": 2, "power_w": 1000},
            permissions=("device.control",),
        )


@pytest.mark.asyncio
async def test_device_broker_safe_range_denied():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = DeviceControlBroker(settings)
    broker.synthetic.register_device(site_id=1, device_id="dev-1")
    broker.grant_lease(runtime_instance_id="r1", site_id=1, device_id="dev-1", capability="device.control")
    with pytest.raises(ValueError, match="safe range"):
        await broker.command(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            capability="device.control",
            command="set_power",
            params={"device_id": "dev-1", "site_id": 1, "power_w": 999999},
            permissions=("device.control",),
        )
