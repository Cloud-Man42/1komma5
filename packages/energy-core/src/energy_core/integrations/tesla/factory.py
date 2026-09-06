"""Tesla vehicle provider factory."""

from __future__ import annotations

import os
from typing import Any

from energy_core.config import Settings
from energy_core.db.models import VehicleProviderConnectionModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.integrations.tesla.client import TeslaFleetClient
from energy_core.integrations.tesla.config import build_tesla_connection_info
from energy_core.integrations.tesla.mock import TeslaMockClient
from energy_core.integrations.tesla.provider import TeslaFleetVehicleProvider
from energy_core.secrets import SecretBox, SecretBoxError


async def build_tesla_provider(
    row: VehicleProviderConnectionModel,
    provider_repo: VehicleProviderRepository,
    secret_box: SecretBox,
    settings: Settings,
    session_factory: Any,
) -> TeslaFleetVehicleProvider:
    _ = settings, session_factory
    refresh_token = ""
    if row.encrypted_refresh_token:
        try:
            refresh_token = secret_box.decrypt(row.encrypted_refresh_token)
        except SecretBoxError:
            refresh_token = ""
    connection = build_tesla_connection_info(
        region=row.region,
        client_id=os.getenv("TESLA_CLIENT_ID"),
        client_secret=os.getenv("TESLA_CLIENT_SECRET"),
        refresh_token=refresh_token or None,
    )
    if connection.mock or not connection.ready:
        client: TeslaFleetClient | TeslaMockClient = TeslaMockClient()
        return TeslaFleetVehicleProvider(client=client, mock=True)
    client = TeslaFleetClient(
        region=connection.region,
        client_id=os.getenv("TESLA_CLIENT_ID", ""),
        client_secret=os.getenv("TESLA_CLIENT_SECRET", ""),
        refresh_token=refresh_token,
    )
    return TeslaFleetVehicleProvider(client=client, mock=False)


def is_tesla_provider(provider: object) -> bool:
    return isinstance(provider, TeslaFleetVehicleProvider)
