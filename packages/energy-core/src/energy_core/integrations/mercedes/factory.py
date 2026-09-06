"""Mercedes vehicle provider factory."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Callable, Protocol, runtime_checkable

from energy_core.db.models import VehicleProviderConnectionModel
from energy_core.secrets import SecretBox
from energy_core.vehicles.mercedes.auth.token_store import MercedesTokenBundle
from energy_core.vehicles.mercedes.provider import MercedesProvider


@runtime_checkable
class MercedesManagedProvider(Protocol):
    provider_id: str
    connection_manager: Any
    mapper: Any
    rest_client: Any
    token_store: Any

    async def login(self, email: str, password: str) -> MercedesTokenBundle: ...
    async def discover(self) -> tuple[Any, ...]: ...
    async def connect(self) -> None: ...
    async def sync_from_rest(self, *, vins: tuple[str, ...] | None = None) -> tuple[Any, ...]: ...
    async def close(self) -> None: ...


def is_mercedes_provider(provider: object) -> bool:
    return isinstance(provider, MercedesProvider)


def build_mercedes_provider(
    row: VehicleProviderConnectionModel,
    *,
    token_bundle: MercedesTokenBundle | None = None,
    device_guid: str | None = None,
) -> MercedesProvider:
    return MercedesProvider(
        region=row.region,
        device_guid=device_guid or row.device_guid or str(uuid.uuid4()),
        token_bundle=token_bundle,
    )


def wire_supervisor_token_callbacks(
    provider: MercedesProvider,
    row: VehicleProviderConnectionModel,
    *,
    session_factory,
    secret_box: SecretBox,
) -> None:
    async def persist(bundle: MercedesTokenBundle) -> None:
        from energy_core.db.vehicle_repo import VehicleProviderRepository

        async with session_factory() as session:
            repo = VehicleProviderRepository(session, secret_box=secret_box)
            db_row = await repo.get_for_site(row.site_id)
            if db_row is not None:
                await repo.persist_token_bundle(db_row, bundle)
                await repo.update_runtime_status(db_row, last_token_refresh_at=datetime.now(UTC))
                await session.commit()

    async def reload() -> MercedesTokenBundle | None:
        from energy_core.db.vehicle_repo import VehicleProviderRepository

        async with session_factory() as session:
            repo = VehicleProviderRepository(session, secret_box=secret_box)
            db_row = await repo.get_for_site(row.site_id)
            if db_row is None:
                return None
            return await repo.load_token_bundle_for_update(db_row)

    provider._token_store._persist = persist  # noqa: SLF001
    provider._token_store._reload = reload  # noqa: SLF001


async def build_authenticated_mercedes_provider(
    row: VehicleProviderConnectionModel,
    *,
    load_token: Callable[[VehicleProviderConnectionModel], MercedesTokenBundle | None],
) -> MercedesProvider:
    token_bundle = load_token(row)
    return build_mercedes_provider(row, token_bundle=token_bundle)


__all__ = [
    "MercedesManagedProvider",
    "build_authenticated_mercedes_provider",
    "build_mercedes_provider",
    "is_mercedes_provider",
    "wire_supervisor_token_callbacks",
]
