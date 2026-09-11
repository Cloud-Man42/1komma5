"""Network broker redirect and DNS rebinding defenses (F-12)."""



from __future__ import annotations



from unittest.mock import AsyncMock, patch



import httpx

import pytest



from energy_core.config import Settings

from energy_core.platform.modules.brokers.network_broker import NetworkBroker





@pytest.mark.asyncio

async def test_redirect_to_private_denied():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = NetworkBroker(settings)

    broker.allow_host(module_id="mod-a", site_id=1, host="example.com")

    redirect_response = httpx.Response(

        302,

        headers={"location": "https://127.0.0.1/internal"},

        request=httpx.Request("GET", "https://example.com/start"),

    )

    with patch("httpx.AsyncClient.request", new=AsyncMock(return_value=redirect_response)):

        with pytest.raises(ValueError, match="Forbidden|127"):

            await broker.request(

                runtime_instance_id="r1",

                module_id="mod-a",

                site_id=1,

                url="https://example.com/start",

                permissions=("network.external",),

            )





@pytest.mark.asyncio

async def test_dns_rebinding_private_resolution_denied():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = NetworkBroker(settings)

    broker.allow_host(module_id="mod-a", site_id=1, host="evil.example")

    with patch(

        "energy_core.platform.modules.distribution.url_policy._resolve_all",

        return_value=[__import__("ipaddress").ip_address("10.0.0.5")],

    ):

        with pytest.raises(ValueError, match="forbidden|Forbidden"):

            await broker.request(

                runtime_instance_id="r1",

                module_id="mod-a",

                site_id=1,

                url="https://evil.example/data",

                permissions=("network.external",),

            )





@pytest.mark.asyncio

async def test_network_local_permission_denied():

    settings = Settings(_env_file=None, APP_ENV="test", DATABASE_URL="sqlite+aiosqlite:///:memory:")

    broker = NetworkBroker(settings)

    broker.allow_host(module_id="mod-a", site_id=1, host="192.168.1.10")

    with pytest.raises(PermissionError, match="network.local denied"):

        await broker.request(

            runtime_instance_id="r1",

            module_id="mod-a",

            site_id=1,

            url="https://192.168.1.10/api",

            permissions=("network.local",),

        )


