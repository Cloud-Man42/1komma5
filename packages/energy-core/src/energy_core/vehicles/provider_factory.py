"""Registry-based vehicle provider factory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from energy_core.config import Settings
from energy_core.db.models import VehicleProviderConnectionModel
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox, SecretBoxError
from energy_core.vehicles.mock.provider import MockVehicleProvider, MockVehicleScenario

ProviderBuilder = Callable[
    [VehicleProviderConnectionModel, VehicleProviderRepository, SecretBox, Settings, Any],
    Awaitable[Any],
]


async def _build_mock_provider(
    row: VehicleProviderConnectionModel,
    provider_repo: VehicleProviderRepository,
    secret_box: SecretBox,
    settings: Settings,
    session_factory: Any,
) -> MockVehicleProvider:
    _ = row, provider_repo, secret_box, settings, session_factory
    return MockVehicleProvider(scenario=MockVehicleScenario.CONNECTED_IDLE)


async def _build_mercedes_provider(
    row: VehicleProviderConnectionModel,
    provider_repo: VehicleProviderRepository,
    secret_box: SecretBox,
    settings: Settings,
    session_factory: Any,
) -> Any:
    from energy_core.integrations.mercedes.factory import (
        build_mercedes_provider,
        wire_supervisor_token_callbacks,
    )

    _ = settings
    try:
        token_bundle = provider_repo.load_token_bundle(row)
    except SecretBoxError:
        token_bundle = None
    provider = build_mercedes_provider(row, token_bundle=token_bundle)
    wire_supervisor_token_callbacks(
        provider,
        row,
        session_factory=session_factory,
        secret_box=secret_box,
    )
    return provider


async def _build_tesla_provider(
    row: VehicleProviderConnectionModel,
    provider_repo: VehicleProviderRepository,
    secret_box: SecretBox,
    settings: Settings,
    session_factory: Any,
) -> Any:
    from energy_core.integrations.tesla.factory import build_tesla_provider

    return await build_tesla_provider(row, provider_repo, secret_box, settings, session_factory)


_PROVIDER_REGISTRY: dict[str, ProviderBuilder] = {
    "mercedes": _build_mercedes_provider,
    "mock": _build_mock_provider,
    "tesla": _build_tesla_provider,
}


async def build_supervisor_provider(
    row: VehicleProviderConnectionModel,
    provider_repo: VehicleProviderRepository,
    *,
    session_factory,
    secret_box: SecretBox,
    settings: Settings,
) -> Any:
    if settings.app_env.value == "test":
        return await _build_mock_provider(row, provider_repo, secret_box, settings, session_factory)
    provider_key = (row.provider or "mercedes").strip().lower()
    builder = _PROVIDER_REGISTRY.get(provider_key)
    if builder is None:
        raise ValueError(f"Unknown vehicle provider '{provider_key}'")
    return await builder(row, provider_repo, secret_box, settings, session_factory)


def is_mock_vehicle_provider(provider: object) -> bool:
    return isinstance(provider, MockVehicleProvider)
