"""Provider-dispatched discovery tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from energy_core.integrations.heartbeat.discovery_service import (
    discover_account_installations,
    discover_system_id_for_serial,
)
from energy_core.integrations.heartbeat.gridx_client import GridXClient, GridXCredentials
from energy_core.integrations.heartbeat.providers import HeartbeatBackendProvider
from energy_core.integrations.heartbeat.serial_matcher import SerialMatchResult


@pytest.mark.asyncio
async def test_discover_gridx_installations_from_systems_list():
    client = GridXClient(
        GridXCredentials(api_url="https://api.gridx.de", api_token="token"),
        account_id=1,
    )
    client.fetch_account = AsyncMock(return_value={"id": "acct-1"})
    client._request = AsyncMock(
        return_value=[
            {
                "id": "91a0e8fc-6e8d-4131-bc49-245d7f3369d9",
                "name": "Denmark",
                "gatewayId": "40a3b35b-5b7d-4de1-b045-e4f1728cfe74",
            }
        ],
    )
    client.fetch_system = AsyncMock(return_value={"id": "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"})
    client.fetch_gateway_appliances = AsyncMock(
        return_value=[{"serialNumber": "K183-600-000-021-000-P-X", "systemId": "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"}],
    )

    session = MagicMock()
    with patch(
        "energy_core.integrations.heartbeat.discovery_service.create_heartbeat_client",
        new=AsyncMock(return_value=client),
    ):
        report = await discover_account_installations(
            session,
            1,
            provider=HeartbeatBackendProvider.GRIDX.value,
            api_url="https://api.gridx.de",
        )

    assert report.authentication_ok is True
    assert len(report.installations) >= 1


@pytest.mark.asyncio
async def test_discover_serial_denmark_fixture():
    serial = "K183-600-000-021-000-P-X"
    client = MagicMock()
    client._request = AsyncMock(
        side_effect=[
            [{"serialNumber": serial, "systemId": "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"}],
        ],
    )

    session = MagicMock()
    with patch(
        "energy_core.integrations.heartbeat.discovery_service.create_heartbeat_client",
        new=AsyncMock(return_value=client),
    ), patch(
        "energy_core.integrations.heartbeat.discovery_service._discover_onekommafive",
        new=AsyncMock(
            return_value=(
                [],
                ("/v1/systems",),
                [[{"serialNumber": serial, "systemId": "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"}]],
            ),
        ),
    ):
        result = await discover_system_id_for_serial(session, 1, serial)

    assert result.found is True
    assert result.resolved_system_id == "91a0e8fc-6e8d-4131-bc49-245d7f3369d9"
