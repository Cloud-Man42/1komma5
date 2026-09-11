"""Module device onboarding orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings, get_settings
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.models import EvChargerModel
from energy_core.db.site_module_repo import SiteModuleRepository
from energy_core.platform.modules.service import SiteModuleService
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from energy_core.providers.module_onboarding import get_onboard_handler


class OnboardError(Exception):
    def __init__(self, message: str, *, code: str = "onboard_failed") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class OnboardDeviceResult:
    device_type: str
    device_id: int
    name: str
    external_id: str
    manufacturer: str = ""
    model: str = ""


@dataclass(frozen=True, slots=True)
class ModuleOnboardResult:
    module_id: str
    enabled: bool
    runtime_status: str
    health_status: str
    device: OnboardDeviceResult | None = None
    capabilities: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()
    message: str = ""


class ModuleOnboardService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()

    async def onboard(
        self,
        site_id: int,
        module_id: str,
        payload: dict[str, Any],
    ) -> ModuleOnboardResult:
        if module_id == "integration.chargeamps":
            return await self._onboard_chargeamps(site_id, payload)
        raise OnboardError(f"Onboarding not implemented for {module_id}", code="unsupported_module")

    async def _onboard_chargeamps(self, site_id: int, payload: dict[str, Any]) -> ModuleOnboardResult:
        external_id = str(payload.get("external_device_id") or payload.get("external_charger_id") or "").strip()
        if not external_id:
            raise OnboardError("external_device_id is required", code="invalid_configuration")
        friendly_name = str(payload.get("friendly_name") or payload.get("name") or "Charge Amps Halo").strip()
        api_key = payload.get("api_key")
        repo = EvChargerRepository(self._session)
        existing = await self._session.scalar(
            select(EvChargerModel).where(
                EvChargerModel.site_id == site_id,
                EvChargerModel.external_charger_id == external_id,
            )
        )
        if existing is not None:
            raise OnboardError(
                f"Device already exists for external id {external_id}",
                code="DEVICE_ALREADY_EXISTS",
            )
        module_repo = SiteModuleRepository(self._session)
        pending_secrets = await module_repo.get_secure_secrets(site_id, "integration.chargeamps")
        resolved_api_key = str(api_key or pending_secrets.get("api_key") or "").strip() or None
        charger = await repo.create(
            site_id,
            name=friendly_name,
            manufacturer=str(payload.get("manufacturer") or "ChargeAmps"),
            model=str(payload.get("model") or "Halo"),
            control_source="chargeamp",
            chargeamp_charger_id=external_id,
            external_charger_id=external_id,
            bridge_enabled=bool(payload.get("bridge_enabled", True)),
            chargeamps_api_key=resolved_api_key,
            manufacturer_id=str(payload.get("manufacturer_id") or "chargeamps"),
            model_id=str(payload.get("model_id") or "halo"),
            integration_method=str(payload.get("integration_method") or "CHARGE_AMPS_CLOUD"),
        )
        if resolved_api_key:
            await module_repo.clear_secure_secrets(site_id, "integration.chargeamps")
        handler = get_onboard_handler("chargeamps", self._session, settings=self._settings)
        test = await handler.test_connection(site_id)
        if not test.success:
            await self._session.delete(charger)
            await self._session.flush()
            raise OnboardError(test.message, code="CONNECTION_FAILED")
        service = SiteModuleService(self._session, settings=self._settings)
        await service.set_enabled(site_id, "integration.chargeamps", True)
        invalidate_site_module_cache(site_id)
        resolver = SiteModuleResolver(self._session, settings=self._settings)
        modules = await resolver.list_modules(site_id, use_cache=False)
        module_state = next((item for item in modules if item.module_id == "integration.chargeamps"), None)
        return ModuleOnboardResult(
            module_id="integration.chargeamps",
            enabled=True if module_state is None else module_state.enabled,
            runtime_status=module_state.runtime_status.value if module_state else "unknown",
            health_status=module_state.health_status.value if module_state else "unknown",
            device=OnboardDeviceResult(
                device_type="ev_charger",
                device_id=charger.id,
                name=charger.name,
                external_id=external_id,
                manufacturer=charger.manufacturer,
                model=charger.model,
            ),
            capabilities=tuple({"name": cap.name, "kind": cap.kind, "available": cap.available} for cap in test.capabilities),
            warnings=(),
            message="Charge Amps device linked and module enabled",
        )
