"""Per-site module configuration API."""

from __future__ import annotations

import json
from typing import Any

from app.admin_audit_helpers import audit_admin_mutation
from app.user_auth import require_permission
from app.deps import get_app_settings, get_db_session
from app.rate_limits import connection_test_rate_limiter
from energy_core.config import Settings
from energy_core.db.repositories import SiteRepository
from energy_core.platform.modules.aliases import CANONICAL_TO_LEGACY, resolve_module_id
from energy_core.platform.modules.module_config_service import ModuleConfigService
from energy_core.platform.modules.catalog_serialization import serialize_module_descriptor
from energy_core.providers.module_apply import ModuleApplyService
from energy_core.providers.module_onboard import ModuleOnboardService, OnboardError
from energy_core.providers.module_onboarding import get_onboard_handler
from energy_core.platform.modules.registry import default_module_registry
from energy_core.platform.modules.service import SiteModuleService
from energy_core.platform.modules.site_modules import SiteModuleResolver, invalidate_site_module_cache
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["modules"])


class SiteModuleUpdateRequest(BaseModel):
    enabled: bool


class SiteModuleResponse(BaseModel):
    module_id: str
    legacy_module_id: str | None = None
    name: str
    version: str
    module_type: str
    enabled: bool
    activation: str
    runtime_status: str
    health_status: str
    capabilities_provided: list[str]
    capabilities_required: list[str]
    optional_capabilities: list[str]
    missing_required_capabilities: list[str]
    missing_optional_capabilities: list[str]
    can_start: bool
    last_error: str | None = None
    configuration_schema: dict = Field(default_factory=dict)
    onboardable: bool = False
    device_categories: list[str] = Field(default_factory=list)
    connection_types: list[str] = Field(default_factory=list)
    can_disable: bool = True
    supports_discovery: bool = False
    dependencies: list[str] = Field(default_factory=list)
    package_source: str | None = None
    installed_version: str | None = None
    publisher: str | None = None
    package_state: str | None = None
    rollback_available: bool = False
    update_available: bool = False


class ModuleConfigResponse(BaseModel):
    module_id: str
    config: dict = Field(default_factory=dict)
    configured_fields: dict[str, bool] = Field(default_factory=dict)
    restart_required: str = "none"
    configuration_active: bool = True
    effectively_configured: bool = False
    configuration_status: str = "incomplete"


class ModuleApplyResponse(BaseModel):
    module_id: str
    success: bool
    message: str
    runtime_status: str
    health_status: str


class ModuleOnboardRequest(BaseModel):
    external_device_id: str | None = None
    external_charger_id: str | None = None
    friendly_name: str | None = None
    name: str | None = None
    api_key: str | None = None
    bridge_enabled: bool = True
    manufacturer: str | None = None
    model: str | None = None
    manufacturer_id: str | None = None
    model_id: str | None = None
    integration_method: str | None = None


class ModuleConfigUpdateRequest(BaseModel):
    config: dict = Field(default_factory=dict)


class ConnectionTestCapability(BaseModel):
    name: str
    kind: str
    available: bool


class OnboardDeviceResponse(BaseModel):
    device_type: str
    device_id: int
    name: str
    external_id: str
    manufacturer: str = ""
    model: str = ""


class ModuleOnboardResponse(BaseModel):
    module_id: str
    enabled: bool
    runtime_status: str
    health_status: str
    device: OnboardDeviceResponse | None = None
    capabilities: list[ConnectionTestCapability] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str = ""


class DiscoveryDeviceResponse(BaseModel):
    external_id: str
    name: str
    device_type: str
    manufacturer: str = ""
    model: str = ""


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    devices_found: list[DiscoveryDeviceResponse] = Field(default_factory=list)
    capabilities: list[ConnectionTestCapability] = Field(default_factory=list)
    latency_ms: int | None = None


class DiscoveryResponse(BaseModel):
    supported: bool
    message: str = ""
    devices: list[DiscoveryDeviceResponse] = Field(default_factory=list)


def _serialize_state(state) -> dict[str, Any]:
    legacy = CANONICAL_TO_LEGACY.get(state.module_id)
    descriptor = default_module_registry.get(state.module_id)
    payload = SiteModuleResponse(
        module_id=state.module_id,
        legacy_module_id=legacy,
        name=state.name,
        version=state.version,
        module_type=state.module_type.value,
        enabled=state.enabled,
        activation=state.activation.value,
        runtime_status=state.runtime_status.value,
        health_status=state.health_status.value,
        capabilities_provided=list(state.capabilities_provided),
        capabilities_required=list(state.capabilities_required),
        optional_capabilities=list(state.optional_capabilities),
        missing_required_capabilities=list(state.missing_required_capabilities),
        missing_optional_capabilities=list(state.missing_optional_capabilities),
        can_start=state.can_start,
        last_error=state.last_error,
        configuration_schema=dict(descriptor.configuration_schema) if descriptor else {},
        onboardable=descriptor.onboardable if descriptor else False,
        device_categories=list(descriptor.device_categories) if descriptor else [],
        connection_types=list(descriptor.connection_types) if descriptor else [],
        can_disable=descriptor.can_disable if descriptor else True,
        supports_discovery=descriptor.supports_discovery if descriptor else False,
        dependencies=list(descriptor.dependencies) if descriptor else [],
        package_source=descriptor.package_source.value if descriptor else None,
        installed_version=descriptor.installed_version if descriptor else None,
        publisher=descriptor.publisher if descriptor else None,
        package_state=descriptor.package_state if descriptor else None,
        rollback_available=False,
        update_available=False,
    ).model_dump()
    return payload


@router.get("/sites/{slug}/modules")
async def list_site_modules(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    resolver = SiteModuleResolver(session, settings=settings)
    modules = await resolver.list_modules(site.id)
    return {"site_slug": slug, "modules": [_serialize_state(state) for state in modules]}


@router.get("/sites/{slug}/modules/{module_id}")
async def get_site_module(
    slug: str,
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    resolver = SiteModuleResolver(session, settings=settings)
    modules = await resolver.list_modules(site.id)
    for state in modules:
        if state.module_id == canonical:
            return _serialize_state(state)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")


@router.put("/sites/{slug}/modules/{module_id}")
async def update_site_module(
    slug: str,
    module_id: str,
    body: SiteModuleUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> dict:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    if default_module_registry.get(canonical) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    if body.enabled:
        from energy_core.db.installed_package_repo import InstalledPackageRepository
        from energy_core.platform.modules.packages.types import PackageState

        package_row = await InstalledPackageRepository(session).get(canonical)
        if package_row is not None and package_row.package_state == PackageState.QUARANTINED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "PACKAGE_QUARANTINED",
                    "message": "Package is quarantined and cannot be enabled",
                },
            )

    resolver = SiteModuleResolver(session, settings=settings)
    if not body.enabled:
        check = await resolver.can_disable(site.id, canonical)
        if not check.allowed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": check.reason or "Cannot disable module",
                    "dependent_modules": list(check.dependent_modules),
                },
            )
    try:
        service = SiteModuleService(session, settings=settings)
        state = await service.set_enabled(site.id, canonical, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.enabled" if body.enabled else "module.disabled",
        site_slug=slug,
        resource_type="module",
        resource_id=canonical,
        summary={"enabled": body.enabled},
    )
    await session.commit()
    invalidate_site_module_cache(site.id)
    return _serialize_state(state)


def _config_response(view) -> ModuleConfigResponse:
    return ModuleConfigResponse(
        module_id=view.module_id,
        config=view.config,
        configured_fields=view.configured_fields,
        restart_required=view.restart_required.value,
        configuration_active=view.configuration_active,
        effectively_configured=view.effectively_configured,
        configuration_status=view.configuration_status,
    )


@router.get("/sites/{slug}/modules/{module_id}/config", response_model=ModuleConfigResponse)
async def get_module_config(
    slug: str,
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ModuleConfigResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    if default_module_registry.get(canonical) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    try:
        view = await ModuleConfigService(session, settings=settings).get_config(site.id, canonical)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _config_response(view)


@router.put("/sites/{slug}/modules/{module_id}/config", response_model=ModuleConfigResponse)
async def update_module_config(
    slug: str,
    module_id: str,
    body: ModuleConfigUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ModuleConfigResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    if default_module_registry.get(canonical) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    service = ModuleConfigService(session, settings=settings)
    try:
        view = await service.update_config(site.id, canonical, body.config)
    except ValueError as exc:
        raw = str(exc)
        try:
            errors = json.loads(raw)
            if isinstance(errors, dict):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors) from exc
        except json.JSONDecodeError:
            pass
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=raw) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.config.update",
        site_slug=slug,
        resource_type="module",
        resource_id=canonical,
        summary={"fields": list(body.config.keys())},
    )
    await session.commit()
    invalidate_site_module_cache(site.id)
    return _config_response(view)


def _connection_test_response(result) -> ConnectionTestResponse:
    return ConnectionTestResponse(
        success=result.success,
        message=result.message,
        devices_found=[
            DiscoveryDeviceResponse(
                external_id=device.external_id,
                name=device.name,
                device_type=device.device_type,
                manufacturer=device.manufacturer,
                model=device.model,
            )
            for device in result.devices_found
        ],
        capabilities=[
            ConnectionTestCapability(name=cap.name, kind=cap.kind, available=cap.available)
            for cap in result.capabilities
        ],
        latency_ms=result.latency_ms,
    )


@router.post("/sites/{slug}/modules/{module_id}/test-connection", response_model=ConnectionTestResponse)
async def test_module_connection(
    slug: str,
    module_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ConnectionTestResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    descriptor = default_module_registry.get(canonical)
    if descriptor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if not descriptor.onboard_handler:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Module has no connection test")
    rate_key = f"{slug}:{canonical}"
    if not connection_test_rate_limiter.check(rate_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Connection test rate limited")
    try:
        handler = get_onboard_handler(descriptor.onboard_handler, session, settings=settings)
        result = await handler.test_connection(site.id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.test_connection",
        site_slug=slug,
        resource_type="module",
        resource_id=canonical,
        summary={"success": result.success},
    )
    await session.commit()
    return _connection_test_response(result)


@router.post("/sites/{slug}/modules/{module_id}/discover", response_model=DiscoveryResponse)
async def discover_module_devices(
    slug: str,
    module_id: str,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> DiscoveryResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    descriptor = default_module_registry.get(canonical)
    if descriptor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if not descriptor.onboard_handler:
        return DiscoveryResponse(supported=False, message="Discovery not supported")
    handler = get_onboard_handler(descriptor.onboard_handler, session, settings=settings)
    result = await handler.discover(site.id)
    return DiscoveryResponse(
        supported=result.supported,
        message=result.message,
        devices=[
            DiscoveryDeviceResponse(
                external_id=device.external_id,
                name=device.name,
                device_type=device.device_type,
                manufacturer=device.manufacturer,
                model=device.model,
            )
            for device in result.devices
        ],
    )


@router.post("/sites/{slug}/modules/{module_id}/apply", response_model=ModuleApplyResponse)
async def apply_module_configuration(
    slug: str,
    module_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ModuleApplyResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    try:
        result = await ModuleApplyService(session, settings=settings).apply_module(site.id, canonical)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit_admin_mutation(
        request,
        session,
        action="module.config.apply",
        site_slug=slug,
        resource_type="module",
        resource_id=canonical,
        summary={"success": result.success},
    )
    await session.commit()
    invalidate_site_module_cache(site.id)
    return ModuleApplyResponse(
        module_id=result.module_id,
        success=result.success,
        message=result.message,
        runtime_status=result.runtime_status,
        health_status=result.health_status,
    )


@router.post("/sites/{slug}/modules/{module_id}/onboard", response_model=ModuleOnboardResponse)
async def onboard_module_device(
    slug: str,
    module_id: str,
    body: ModuleOnboardRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(require_permission("modules.manage")),
) -> ModuleOnboardResponse:
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    canonical = resolve_module_id(module_id)
    payload = body.model_dump(exclude_none=True)
    try:
        result = await ModuleOnboardService(session, settings=settings).onboard(site.id, canonical, payload)
    except OnboardError as exc:
        status_code = status.HTTP_409_CONFLICT if exc.code == "DEVICE_ALREADY_EXISTS" else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(
            status_code=status_code,
            detail={"message": str(exc), "code": exc.code},
        ) from exc
    await audit_admin_mutation(
        request,
        session,
        action="device.onboarded" if result.device else "module.onboarded",
        site_slug=slug,
        resource_type="module",
        resource_id=canonical,
        summary={
            "device_type": result.device.device_type if result.device else None,
            "device_id": result.device.device_id if result.device else None,
            "external_id": result.device.external_id if result.device else None,
        },
    )
    await session.commit()
    invalidate_site_module_cache(site.id)
    return ModuleOnboardResponse(
        module_id=result.module_id,
        enabled=result.enabled,
        runtime_status=result.runtime_status,
        health_status=result.health_status,
        device=(
            OnboardDeviceResponse(
                device_type=result.device.device_type,
                device_id=result.device.device_id,
                name=result.device.name,
                external_id=result.device.external_id,
                manufacturer=result.device.manufacturer,
                model=result.device.model,
            )
            if result.device
            else None
        ),
        capabilities=[
            ConnectionTestCapability(name=cap["name"], kind=cap["kind"], available=cap["available"])
            for cap in result.capabilities
        ],
        warnings=list(result.warnings),
        message=result.message,
    )
