"""Integration-specific configuration apply handlers (credential delegation)."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.consumer_repo import ConsumerRepository
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import SiteModel
from energy_core.db.site_module_repo import SiteModuleRepository
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.platform.modules.onboarding.types import RestartRequired
from energy_core.secrets import SecretBox, SecretBoxError


class ConfigApplyHandler(Protocol):
    async def apply(
        self,
        session: AsyncSession,
        site_id: int,
        submitted: dict[str, Any],
        merged: dict[str, Any],
        *,
        settings: Settings | None = None,
    ) -> RestartRequired: ...


class MercedesConfigHandler:
    async def apply(
        self,
        session: AsyncSession,
        site_id: int,
        submitted: dict[str, Any],
        merged: dict[str, Any],
        *,
        settings: Settings | None = None,
    ) -> RestartRequired:
        repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
        row = await repo.get_or_create(site_id)
        username = submitted.get("username")
        password = submitted.get("password")
        updates: dict[str, Any] = {}
        if username is not None:
            updates["username"] = str(username)
        if password:
            updates["password"] = str(password)
        if updates:
            try:
                await repo.update_config(row, **updates)
            except SecretBoxError as exc:
                raise ValueError(str(exc)) from exc
            return RestartRequired.MODULE
        return RestartRequired.NONE


class ChargeAmpsConfigHandler:
    async def apply(
        self,
        session: AsyncSession,
        site_id: int,
        submitted: dict[str, Any],
        merged: dict[str, Any],
        *,
        settings: Settings | None = None,
    ) -> RestartRequired:
        repo = EvChargerRepository(session)
        module_repo = SiteModuleRepository(session)
        api_key = submitted.get("api_key")
        email = submitted.get("email")
        password = submitted.get("password")
        changed = False
        if api_key:
            chargers = await repo.list_for_site(site_id)
            if chargers:
                for charger in chargers:
                    await repo.update(charger, chargeamps_api_key=str(api_key))
                changed = True
            else:
                await module_repo.set_secure_secrets(site_id, "integration.chargeamps", {"api_key": str(api_key)})
                changed = True
        secure_updates: dict[str, str] = {}
        if email:
            secure_updates["email"] = str(email)
        if password:
            secure_updates["password"] = str(password)
        if secure_updates:
            await module_repo.merge_secure_secrets(site_id, "integration.chargeamps", secure_updates)
            changed = True
        return RestartRequired.MODULE if changed else RestartRequired.NONE


class HeartbeatConfigHandler:
    async def apply(
        self,
        session: AsyncSession,
        site_id: int,
        submitted: dict[str, Any],
        merged: dict[str, Any],
        *,
        settings: Settings | None = None,
    ) -> RestartRequired:
        external_id = submitted.get("external_system_id") or merged.get("external_system_id")
        if not external_id:
            return RestartRequired.NONE
        site = await session.get(SiteModel, site_id)
        if site is None:
            return RestartRequired.NONE
        site.external_system_id = str(external_id)
        await session.flush()
        return RestartRequired.INTEGRATION


class ArcticSpaConfigHandler:
    async def apply(
        self,
        session: AsyncSession,
        site_id: int,
        submitted: dict[str, Any],
        merged: dict[str, Any],
        *,
        settings: Settings | None = None,
    ) -> RestartRequired:
        site = await session.get(SiteModel, site_id)
        if site is None:
            return RestartRequired.NONE
        repo = ConsumerRepository(session)
        consumer, _config = await repo.get_or_create_spa(site)
        api_key = submitted.get("api_key")
        spa_id = submitted.get("spa_id") or merged.get("spa_id")
        await repo.update_spa_config(
            consumer.id,
            api_key=str(api_key) if api_key else None,
            external_spa_id=str(spa_id) if spa_id else None,
            integration_enabled=True,
        )
        return RestartRequired.MODULE


_HANDLERS: dict[str, ConfigApplyHandler] = {
    "integration.mercedes": MercedesConfigHandler(),
    "integration.chargeamps": ChargeAmpsConfigHandler(),
    "integration.heartbeat": HeartbeatConfigHandler(),
    "integration.arctic_spa": ArcticSpaConfigHandler(),
}


async def apply_integration_config(
    session: AsyncSession,
    module_id: str,
    site_id: int,
    submitted: dict[str, Any],
    merged: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> RestartRequired:
    handler = _HANDLERS.get(module_id)
    if handler is None:
        return RestartRequired.NONE
    return await handler.apply(session, site_id, submitted, merged, settings=settings)
