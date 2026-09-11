"""Cross-site isolation tests."""

from __future__ import annotations

import pytest

from energy_core.config import Settings
from energy_core.platform.modules.brokers.data_read_broker import DataReadBroker
from energy_core.platform.modules.brokers.secret_broker import SecretBroker


@pytest.mark.asyncio
async def test_data_read_cross_site_denied():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = DataReadBroker(settings)
    broker.seed(site_id=2, capability="read_status", payload={"value": "secret"})
    with pytest.raises(PermissionError, match="cross-site"):
        await broker.read(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            capability="read_status",
            params={"site_id": 2},
            permissions=("read_status",),
        )


@pytest.mark.asyncio
async def test_secret_enumeration_denied_without_permission():
    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")
    broker = SecretBroker(settings)
    broker.register_secret(module_id="mod-a", site_id=1, secret_ref="api-key", value="secret")
    with pytest.raises(PermissionError):
        await broker.get_secret(
            runtime_instance_id="r1",
            module_id="mod-a",
            site_id=1,
            secret_ref="api-key",
            permissions=(),
        )
