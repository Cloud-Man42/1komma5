"""Build Zaptec REST clients and adapters."""

from __future__ import annotations

import os

from energy_core.chargers.framework.models import ChargerAdapter, ChargerConfiguration
from energy_core.integrations.zaptec.adapter import ZaptecRestAdapter
from energy_core.integrations.zaptec.client import ZaptecRestClient
from energy_core.integrations.zaptec.config import build_zaptec_connection_info
from energy_core.integrations.zaptec.mock import ZaptecMockClient


def build_zaptec_adapter(config: ChargerConfiguration) -> ChargerAdapter:
    settings = config.connection_settings or {}
    charger_uuid = (
        config.external_charger_id
        or settings.get("charger_id")
        or settings.get("account_id")
    )
    installation_id = settings.get("installation_id") or settings.get("account_id")
    username = settings.get("username") or os.getenv("ZAPTEC_USERNAME")
    password = settings.get("password") or os.getenv("ZAPTEC_PASSWORD")
    connection = build_zaptec_connection_info(
        charger_id=str(charger_uuid) if charger_uuid else None,
        installation_id=str(installation_id) if installation_id else None,
        username=str(username) if username else None,
        password=str(password) if password else None,
    )
    if connection.mock or not connection.ready:
        client: ZaptecRestClient | ZaptecMockClient = ZaptecMockClient(
            charger_id=str(charger_uuid or f"mock-{config.charger_id}"),
            installation_id=str(installation_id) if installation_id else None,
        )
    else:
        client = ZaptecRestClient(username=str(username), password=str(password))
    return ZaptecRestAdapter(
        manufacturer_id=config.manufacturer_id,
        model_id=config.model_id,
        client=client,
        charger_id=str(charger_uuid) if charger_uuid else None,
        installation_id=str(installation_id) if installation_id else None,
        connection_info=connection,
    )


def is_zaptec_adapter(adapter: object) -> bool:
    return isinstance(adapter, ZaptecRestAdapter)
