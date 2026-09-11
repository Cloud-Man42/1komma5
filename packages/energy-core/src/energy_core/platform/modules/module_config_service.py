"""Site module configuration read/write service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.db.site_module_repo import SiteModuleRepository
from energy_core.platform.modules.aliases import resolve_module_id
from energy_core.platform.modules.config_schema import mask_config_for_response, validate_config_values
from energy_core.platform.modules.onboarding.types import RestartRequired
from energy_core.platform.modules.registry import default_module_registry
from energy_core.providers.module_config_handlers import apply_integration_config
from energy_core.providers.module_onboarding import get_onboard_handler


@dataclass(frozen=True, slots=True)
class ModuleConfigView:
    module_id: str
    config: dict[str, Any]
    configured_fields: dict[str, bool]
    restart_required: RestartRequired
    configuration_active: bool
    effectively_configured: bool
    configuration_status: str


class ModuleConfigService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = SiteModuleRepository(session)

    async def get_config(self, site_id: int, module_id: str) -> ModuleConfigView:
        canonical = resolve_module_id(module_id)
        descriptor = default_module_registry.get(canonical)
        if descriptor is None:
            raise ValueError("Module not found")
        stored = await self._repo.get_public_config(site_id, canonical)
        if canonical == "integration.heartbeat" and "external_system_id" not in stored:
            from energy_core.db.models import SiteModel

            site = await self._session.get(SiteModel, site_id)
            if site and site.external_system_id:
                stored = {**stored, "external_system_id": site.external_system_id}
        configured_secrets: set[str] = set()
        secure = await self._repo.get_secure_secrets(site_id, canonical)
        configured_secrets.update(key for key, value in secure.items() if value)
        if descriptor.onboard_handler:
            try:
                handler = get_onboard_handler(descriptor.onboard_handler, self._session, settings=self._settings)
                configured_secrets.update(await handler.configured_secrets(site_id))
            except KeyError:
                pass
        public, configured_fields = mask_config_for_response(
            descriptor.configuration_schema,
            stored,
            configured_secrets=configured_secrets,
        )
        effectively_configured = self._effective_configuration(canonical, configured_fields, configured_secrets)
        return ModuleConfigView(
            module_id=canonical,
            config=public,
            configured_fields=configured_fields,
            restart_required=RestartRequired.NONE,
            configuration_active=True,
            effectively_configured=effectively_configured,
            configuration_status=self._configuration_status(canonical, effectively_configured, RestartRequired.NONE),
        )

    async def update_config(
        self,
        site_id: int,
        module_id: str,
        values: dict[str, Any],
    ) -> ModuleConfigView:
        canonical = resolve_module_id(module_id)
        descriptor = default_module_registry.get(canonical)
        if descriptor is None:
            raise ValueError("Module not found")
        existing = await self._repo.get_public_config(site_id, canonical)
        configured_secrets: set[str] = set()
        secure = await self._repo.get_secure_secrets(site_id, canonical)
        configured_secrets.update(key for key, value in secure.items() if value)
        if descriptor.onboard_handler:
            handler = get_onboard_handler(descriptor.onboard_handler, self._session, settings=self._settings)
            configured_secrets.update(await handler.configured_secrets(site_id))
        merged = {**existing}
        for key, value in values.items():
            if value is None:
                continue
            field = next(
                (f for f in descriptor.configuration_schema.get("fields", []) if f.get("name") == key),
                None,
            )
            if field and field.get("secret") and value == "":
                continue
            merged[key] = value
        errors = validate_config_values(descriptor.configuration_schema, merged, configured_secrets=configured_secrets)
        if errors:
            raise ValueError(json.dumps(errors))
        public_values = {}
        secret_names = {field["name"] for field in descriptor.configuration_schema.get("fields", []) if field.get("secret")}
        for key, value in merged.items():
            if key not in secret_names:
                public_values[key] = value
        await self._repo.set_config(site_id, canonical, public_values)
        restart = await apply_integration_config(
            self._session,
            canonical,
            site_id,
            values,
            merged,
            settings=self._settings,
        )
        view = await self.get_config(site_id, canonical)
        return ModuleConfigView(
            module_id=view.module_id,
            config=view.config,
            configured_fields=view.configured_fields,
            restart_required=restart,
            configuration_active=restart == RestartRequired.NONE,
            effectively_configured=view.effectively_configured,
            configuration_status=self._configuration_status(canonical, view.effectively_configured, restart),
        )

    def _effective_configuration(
        self,
        module_id: str,
        configured_fields: dict[str, bool],
        configured_secrets: set[str],
    ) -> bool:
        if module_id == "integration.heartbeat":
            has_site = bool(configured_fields.get("external_system_id"))
            has_creds = "password" in configured_secrets or "api_token" in configured_secrets
            return has_site and has_creds
        if module_id == "integration.mercedes":
            return bool(configured_fields.get("username")) and (
                "password" in configured_secrets or "oauth_token" in configured_secrets
            )
        if module_id == "integration.chargeamps":
            return "api_key" in configured_secrets or bool(configured_fields.get("email"))
        if module_id == "integration.arctic_spa":
            return bool(configured_fields.get("spa_id")) and "api_key" in configured_secrets
        return all(configured_fields.values()) if configured_fields else False

    def _configuration_status(
        self,
        module_id: str,
        effectively_configured: bool,
        restart: RestartRequired,
    ) -> str:
        if restart != RestartRequired.NONE:
            return "restart_required"
        if module_id == "integration.heartbeat" and not effectively_configured:
            return "heartbeat_credentials_missing"
        if effectively_configured:
            return "active"
        return "incomplete"
