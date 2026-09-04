"""Energy control API routes."""

from __future__ import annotations

from app.admin_audit_helpers import audit_admin_mutation
from app.admin_auth import require_admin_token
from app.deps import get_db_session, get_site_repository
from app.schemas import (
    EnergyControlActionResponse,
    EnergyControlPreviewRequest,
    EnergyControlRecentResponse,
    EnergyControlResultResponse,
    EnergyControlSettingsUpdateRequest,
    EnergyControlStatusResponse,
)
from energy_core.db.repositories import SiteRepository
from energy_core.energy_control.service import EnergyControlService
from energy_core.energy_control.types import ControlTarget, OptimizationAction
from energy_core.energy_optimizer.types import EnergyAction
from energy_core.price_engine.types import OptimizationMode
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["energy-control"])


def _action_response(record) -> EnergyControlActionResponse:
    return EnergyControlActionResponse(
        id=record.id,
        recorded_at=record.recorded_at,
        optimization_mode=record.optimization_mode.value,
        action=record.action.value,
        target=record.target.value,
        outcome=record.outcome.value,
        dry_run=record.dry_run,
        reason=record.reason,
    )


def _result_response(slug: str, result) -> EnergyControlResultResponse:
    return EnergyControlResultResponse(
        slug=slug,
        action=result.action.value,
        target=result.target.value,
        outcome=result.outcome.value,
        dry_run=result.dry_run,
        reason=result.reason,
        reason_sv=result.reason_sv,
        provider=result.provider,
    )


def _parse_mode(value: str) -> OptimizationMode:
    try:
        return OptimizationMode(value.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown optimization mode '{value}'") from exc


def _parse_action(value: str) -> OptimizationAction:
    try:
        return EnergyAction(value.upper())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown action '{value}'") from exc


def _parse_target(value: str) -> ControlTarget:
    try:
        return ControlTarget(value.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown target '{value}'") from exc


@router.get("/sites/{slug}/energy-control/status", response_model=EnergyControlStatusResponse)
async def get_energy_control_status(
    slug: str,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> EnergyControlStatusResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    service = EnergyControlService(session)
    status = await service.status(site)
    return EnergyControlStatusResponse(
        slug=slug,
        timezone=site.timezone,
        optimization_mode=status.optimization_mode.value,
        control_enabled=status.control_enabled,
        writes_allowed=status.writes_allowed,
        automatic_allowed=status.automatic_allowed,
        provider=status.provider,
        last_action=_action_response(status.last_action) if status.last_action else None,
    )


@router.put("/sites/{slug}/energy-control/settings", response_model=EnergyControlStatusResponse)
async def update_energy_control_settings(
    slug: str,
    payload: EnergyControlSettingsUpdateRequest,
    request: Request,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> EnergyControlStatusResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    mode = _parse_mode(payload.optimization_mode) if payload.optimization_mode is not None else None
    service = EnergyControlService(session)
    status = await service.update_settings(
        site,
        optimization_mode=mode,
        control_enabled=payload.control_enabled,
    )
    await audit_admin_mutation(
        request,
        session,
        action="energy_control.settings.update",
        site_slug=slug,
        resource_type="site",
        resource_id=slug,
        summary=payload.model_dump(exclude_unset=True),
    )
    await session.commit()
    return EnergyControlStatusResponse(
        slug=slug,
        timezone=site.timezone,
        optimization_mode=status.optimization_mode.value,
        control_enabled=status.control_enabled,
        writes_allowed=status.writes_allowed,
        automatic_allowed=status.automatic_allowed,
        provider=status.provider,
        last_action=_action_response(status.last_action) if status.last_action else None,
    )


@router.post("/sites/{slug}/energy-control/preview", response_model=EnergyControlResultResponse)
async def preview_energy_control_action(
    slug: str,
    payload: EnergyControlPreviewRequest,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> EnergyControlResultResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    service = EnergyControlService(session)
    result = await service.preview(
        site,
        _parse_action(payload.action),
        target=_parse_target(payload.target),
    )
    await session.commit()
    return _result_response(slug, result)


@router.post("/sites/{slug}/energy-control/apply", response_model=EnergyControlResultResponse)
async def apply_energy_control_action(
    slug: str,
    payload: EnergyControlPreviewRequest,
    request: Request,
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_admin_token),
) -> EnergyControlResultResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    service = EnergyControlService(session)
    result = await service.apply(
        site,
        _parse_action(payload.action),
        target=_parse_target(payload.target),
    )
    await audit_admin_mutation(
        request,
        session,
        action="energy_control.apply",
        site_slug=slug,
        resource_type="site",
        resource_id=slug,
        summary={"action": payload.action, "target": payload.target, "outcome": result.outcome.value},
    )
    await session.commit()
    return _result_response(slug, result)


@router.get("/sites/{slug}/energy-control/recent", response_model=EnergyControlRecentResponse)
async def get_energy_control_recent(
    slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    site_repo: SiteRepository = Depends(get_site_repository),
    session: AsyncSession = Depends(get_db_session),
) -> EnergyControlRecentResponse:
    site = await site_repo.get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site '{slug}' not found")

    service = EnergyControlService(session)
    actions = await service.recent(site.id, limit=limit)
    return EnergyControlRecentResponse(
        slug=slug,
        actions=[_action_response(a) for a in actions],
    )
