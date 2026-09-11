"""Vehicle command provider wiring (vendor adapters live here)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.commands.errors import VehicleCommandError
from energy_core.vehicles.commands.provider_resolver import IVehicleCommandProvider


async def resolve_vehicle_command_provider(
    session: AsyncSession,
    site_id: int,
    *,
    secret_box: SecretBox | None = None,
) -> IVehicleCommandProvider | None:
    repo = VehicleProviderRepository(session, secret_box=secret_box)
    row = await repo.get_for_site(site_id)
    if row is None or not row.enabled:
        return None
    provider_key = (row.provider or "mercedes").strip().lower()
    if provider_key == "mercedes":
        from energy_core.integrations.mercedes.command_provider import MercedesVehicleCommandProvider

        return MercedesVehicleCommandProvider(row, repo)
    if provider_key == "mock":
        from energy_core.vehicles.commands.mock_provider import MockVehicleCommandProvider

        return MockVehicleCommandProvider()
    raise VehicleCommandError(
        f"Vehicle command provider '{provider_key}' is not supported",
        code="provider_unavailable",
    )
