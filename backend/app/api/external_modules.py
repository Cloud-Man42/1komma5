"""External module site configuration API."""

from __future__ import annotations

from app.deps import get_app_settings, get_db_session
from app.site_access import require_site_with_permission
from app.user_auth import require_authenticated, require_permission
from energy_core.auth.principal import Principal
from energy_core.climate.external_config import ExternalModuleConfigService
from energy_core.config import Settings
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sites", tags=["external-modules"])


class ExternalModuleConfigRequest(BaseModel):
    api_key: str | None = Field(None, min_length=8, max_length=512)
    poll_interval_seconds: int = Field(300, ge=60, le=3600)
    selected_device_ids: list[str] = Field(default_factory=list)


class ExternalModuleConfigResponse(BaseModel):
    module_id: str
    site_slug: str
    credential_configured: bool
    poll_interval_seconds: int
    selected_device_ids: list[str]


@router.get("/{slug}/modules/{module_id}/external-config", response_model=ExternalModuleConfigResponse)
async def get_external_module_config(
    slug: str,
    module_id: str,
    _admin=Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_authenticated),
    settings: Settings = Depends(get_app_settings),
) -> ExternalModuleConfigResponse:
    site = await require_site_with_permission(session, principal, settings, slug, "modules.manage")
    service = ExternalModuleConfigService(session)
    row = await service.get(site_id=site.id, module_id=module_id)
    if row is None:
        return ExternalModuleConfigResponse(
            module_id=module_id,
            site_slug=slug,
            credential_configured=False,
            poll_interval_seconds=300,
            selected_device_ids=[],
        )
    import json

    devices: list[str] = []
    if row.selected_device_ids_json:
        try:
            parsed = json.loads(row.selected_device_ids_json)
            if isinstance(parsed, list):
                devices = [str(d) for d in parsed]
        except json.JSONDecodeError:
            pass
    return ExternalModuleConfigResponse(
        module_id=module_id,
        site_slug=slug,
        credential_configured=bool(row.credential_encrypted),
        poll_interval_seconds=row.poll_interval_seconds,
        selected_device_ids=devices,
    )


@router.put("/{slug}/modules/{module_id}/external-config", response_model=ExternalModuleConfigResponse)
async def upsert_external_module_config(
    slug: str,
    module_id: str,
    body: ExternalModuleConfigRequest,
    _admin=Depends(require_permission("modules.manage")),
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_authenticated),
    settings: Settings = Depends(get_app_settings),
) -> ExternalModuleConfigResponse:
    site = await require_site_with_permission(session, principal, settings, slug, "modules.manage")
    service = ExternalModuleConfigService(session)
    row = await service.upsert(
        site_id=site.id,
        module_id=module_id,
        api_key=body.api_key,
        poll_interval_seconds=body.poll_interval_seconds,
        selected_device_ids=body.selected_device_ids,
    )
    await session.commit()
    import json

    devices: list[str] = []
    if row.selected_device_ids_json:
        try:
            parsed = json.loads(row.selected_device_ids_json)
            if isinstance(parsed, list):
                devices = [str(d) for d in parsed]
        except json.JSONDecodeError:
            pass
    return ExternalModuleConfigResponse(
        module_id=module_id,
        site_slug=slug,
        credential_configured=bool(row.credential_encrypted),
        poll_interval_seconds=row.poll_interval_seconds,
        selected_device_ids=devices,
    )
