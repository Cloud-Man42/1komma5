"""Tests for Zaptec REST client, parsing, and mock."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from energy_core.integrations.zaptec.client import ZaptecApiError, ZaptecRestClient
from energy_core.integrations.zaptec.constants import (
    OPERATION_CHARGING,
    STATE_CHARGE_CURRENT_A,
    STATE_CHARGER_OPERATION_MODE,
    STATE_IS_ONLINE,
    STATE_SESSION_ENERGY_KWH,
    STATE_TOTAL_CHARGE_POWER_W,
)
from energy_core.integrations.zaptec.mock import ZaptecMockClient
from energy_core.integrations.zaptec.parsing import parse_charger_status


def test_parse_charger_status_charging():
    now = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)
    observations = [
        {"stateId": STATE_IS_ONLINE, "valueAsString": "1"},
        {"stateId": STATE_CHARGER_OPERATION_MODE, "valueAsString": str(OPERATION_CHARGING)},
        {"stateId": STATE_TOTAL_CHARGE_POWER_W, "valueAsString": "7200"},
        {"stateId": STATE_SESSION_ENERGY_KWH, "valueAsString": "4.2"},
        {"stateId": STATE_CHARGE_CURRENT_A, "valueAsString": "10.5"},
    ]
    status = parse_charger_status(observations, now=now)
    assert status.online is True
    assert status.charging is True
    assert status.vehicle_connected is True
    assert status.state == "Charging"
    assert status.power_w == 7200.0
    assert status.session_energy_kwh == 4.2
    assert status.charge_current_a == 10.5


def test_parse_charger_status_offline():
    status = parse_charger_status([{"stateId": STATE_IS_ONLINE, "valueAsString": "0"}])
    assert status.online is False
    assert status.charging is False
    assert status.state == "Unknown"


@pytest.mark.asyncio
async def test_zaptec_mock_client_control_commands():
    client = ZaptecMockClient(charger_id="charger-1", installation_id="install-1")
    await client.resume_charging("charger-1")
    status = await client.get_charger_status("charger-1")
    assert status.charging is True
    await client.stop_charging("charger-1")
    status = await client.get_charger_status("charger-1")
    assert status.charging is False
    await client.set_installation_available_current("install-1", available_current_a=10.0)
    await client.resume_charging("charger-1")
    status = await client.get_charger_status("charger-1")
    assert status.charge_current_a == 10.0


@pytest.mark.asyncio
async def test_zaptec_rest_client_fetches_state():
    client = ZaptecRestClient(username="user", password="pass")
    observations = [
        {"stateId": STATE_IS_ONLINE, "valueAsString": "1"},
        {"stateId": STATE_CHARGER_OPERATION_MODE, "valueAsString": str(OPERATION_CHARGING)},
    ]
    with patch.object(client, "get_charger_state", AsyncMock(return_value=observations)):
        status = await client.get_charger_status("charger-1")

    assert status.charging is True
    assert status.state == "Charging"


@pytest.mark.asyncio
async def test_zaptec_rest_client_auth_failure():
    client = ZaptecRestClient(username="user", password="bad")
    with patch.object(
        client,
        "_ensure_token",
        AsyncMock(side_effect=ZaptecApiError("Zaptec auth failed with status 401")),
    ):
        with pytest.raises(ZaptecApiError, match="auth failed"):
            await client.get_charger_state("charger-1")
