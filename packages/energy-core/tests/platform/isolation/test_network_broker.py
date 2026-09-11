"""Network broker SSRF and allowlist tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.brokers.network_broker import NetworkBroker


@pytest.mark.asyncio
async def test_network_denied_without_permission():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = NetworkBroker(settings)
    with pytest.raises(PermissionError, match="network permission"):
        await broker.request(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            url="https://example.com/",
            permissions=("device.read",),
        )


@pytest.mark.asyncio
async def test_network_rejects_unlisted_host():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = NetworkBroker(settings)
    with pytest.raises(ValueError, match="host not allowlisted"):
        await broker.request(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            url="https://example.com/",
            permissions=("network.external",),
        )


@pytest.mark.asyncio
async def test_network_rejects_file_scheme():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = NetworkBroker(settings)
    broker.allow_host(module_id="mod-a", site_id=1, host="example.com")
    with pytest.raises(ValueError):
        await broker.request(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            url="file:///etc/passwd",
            permissions=("network.external",),
        )
