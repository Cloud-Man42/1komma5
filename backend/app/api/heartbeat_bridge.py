"""Heartbeat Virtual EV Bridge API routes."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from app.schemas import (
    HeartbeatBridgeSettingsResponse,
    HeartbeatBridgeSettingsUpdateRequest,
    HeartbeatBridgeStatusResponse,
    HeartbeatDiscoveryRunDetailResponse,
    HeartbeatDiscoveryRunResponse,
    HeartbeatDiscoveryRunResultResponse,
    HeartbeatEvMappingResponse,
    HeartbeatEvMappingUpdateRequest,
    HeartbeatReplayResponse,
    HeartbeatWriteTestResponse,
)
from energy_core.db.ev_charger_repo import EvChargerRepository
from energy_core.db.heartbeat_discovery_repo import HeartbeatDiscoveryRepository
from energy_core.heartbeat.bridge.replay import VirtualChargerReplayService
from energy_core.heartbeat.bridge.service import HeartbeatEvBridgeService
from energy_core.heartbeat.write_test.service import HeartbeatWriteTestService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session

router = APIRouter(tags=["heartbeat-bridge"])
logger = logging.getLogger(__name__)


async def _get_site_or_404(session: AsyncSession, slug: str):
    repo = EvChargerRepository(session)
    site = await repo.get_site_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


@router.post("/sites/{slug}/heartbeat/discovery/run", response_model=HeartbeatDiscoveryRunResultResponse)
async def run_heartbeat_discovery(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatDiscoveryRunResultResponse:
    service = HeartbeatEvBridgeService(session)
    try:
        result, run_id = await service.run_discovery(slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Heartbeat discovery failed for %s", slug)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return HeartbeatDiscoveryRunResultResponse(
        run_id=run_id,
        report_text=result.report_text,
        setup_classification=result.setup_classification.value,
        bridge_lifecycle=result.bridge_lifecycle.value,
        resolved_ev_id=result.resolved_ev_id.heartbeat_ev_id,
        confidence_pct=result.resolved_ev_id.confidence_pct,
        virtual_bridge_suitable=result.virtual_bridge_suitable,
        charging_modes=list(result.charging_modes),
        emic_vehicle_lines=list(result.emic_vehicle_lines),
        warnings=list(result.warnings),
    )


@router.get("/sites/{slug}/heartbeat/discovery/runs", response_model=list[HeartbeatDiscoveryRunResponse])
async def list_heartbeat_discovery_runs(
    slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[HeartbeatDiscoveryRunResponse]:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    runs = await repo.list_runs(site.id, limit=limit)
    return [
        HeartbeatDiscoveryRunResponse(
            id=run.id,
            status=run.status,
            system_id=run.system_id,
            conclusion_class=run.conclusion_class,
            bridge_lifecycle=run.bridge_lifecycle,
            resolved_ev_id=run.resolved_ev_id,
            confidence_pct=run.confidence_pct,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


@router.get(
    "/sites/{slug}/heartbeat/discovery/runs/{run_id}",
    response_model=HeartbeatDiscoveryRunDetailResponse,
)
async def get_heartbeat_discovery_run(
    slug: str,
    run_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatDiscoveryRunDetailResponse:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    run = await repo.get_run(site.id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery run not found")
    report = await repo.get_run_report_json(run_id)
    observations = await repo.list_observations(run_id)
    return HeartbeatDiscoveryRunDetailResponse(
        id=run.id,
        status=run.status,
        system_id=run.system_id,
        conclusion_class=run.conclusion_class,
        bridge_lifecycle=run.bridge_lifecycle,
        resolved_ev_id=run.resolved_ev_id,
        confidence_pct=run.confidence_pct,
        report_text=run.report_text,
        report=report,
        observations=observations,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get("/sites/{slug}/heartbeat/bridge/status", response_model=HeartbeatBridgeStatusResponse)
async def get_heartbeat_bridge_status(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatBridgeStatusResponse:
    service = HeartbeatEvBridgeService(session)
    try:
        data = await service.bridge_status(slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return HeartbeatBridgeStatusResponse(**data)


@router.get("/sites/{slug}/heartbeat/bridge/mappings", response_model=list[HeartbeatEvMappingResponse])
async def list_heartbeat_ev_mappings(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[HeartbeatEvMappingResponse]:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    mappings = await repo.list_mappings(site.id)
    return [
        HeartbeatEvMappingResponse(
            id=m.id,
            heartbeat_ev_id=m.heartbeat_ev_id,
            heartbeat_ev_name=m.heartbeat_ev_name,
            physical_charger_id=m.physical_charger_id,
            vehicle_id=m.vehicle_id,
            provider=m.provider,
            enabled=m.enabled,
            confidence_pct=m.confidence_pct,
            last_discovery_at=m.last_discovery_at,
        )
        for m in mappings
    ]


@router.patch("/sites/{slug}/heartbeat/bridge/mappings/{mapping_id}", response_model=HeartbeatEvMappingResponse)
async def update_heartbeat_ev_mapping(
    slug: str,
    mapping_id: int,
    payload: HeartbeatEvMappingUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatEvMappingResponse:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    mapping = await repo.update_mapping(
        mapping_id,
        site.id,
        enabled=payload.enabled,
        physical_charger_id=payload.physical_charger_id,
        vehicle_id=payload.vehicle_id,
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    await session.commit()
    return HeartbeatEvMappingResponse(
        id=mapping.id,
        heartbeat_ev_id=mapping.heartbeat_ev_id,
        heartbeat_ev_name=mapping.heartbeat_ev_name,
        physical_charger_id=mapping.physical_charger_id,
        vehicle_id=mapping.vehicle_id,
        provider=mapping.provider,
        enabled=mapping.enabled,
        confidence_pct=mapping.confidence_pct,
        last_discovery_at=mapping.last_discovery_at,
    )


@router.get("/sites/{slug}/heartbeat/bridge/settings", response_model=HeartbeatBridgeSettingsResponse)
async def get_heartbeat_bridge_settings(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatBridgeSettingsResponse:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    settings = await repo.get_or_create_bridge_settings(site.id)
    return HeartbeatBridgeSettingsResponse(**asdict(settings))


@router.patch("/sites/{slug}/heartbeat/bridge/settings", response_model=HeartbeatBridgeSettingsResponse)
async def update_heartbeat_bridge_settings(
    slug: str,
    payload: HeartbeatBridgeSettingsUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatBridgeSettingsResponse:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    settings = await repo.update_bridge_settings(site.id, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return HeartbeatBridgeSettingsResponse(**asdict(settings))


@router.post("/sites/{slug}/heartbeat/write-test/run", response_model=HeartbeatWriteTestResponse)
async def run_heartbeat_write_test(
    slug: str,
    dry_run: bool = Query(default=True),
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatWriteTestResponse:
    service = HeartbeatWriteTestService(session)
    try:
        result = await service.run(slug, dry_run=dry_run)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Heartbeat write test failed for %s", slug)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return HeartbeatWriteTestResponse(
        classification=result.classification,
        requested_value=result.requested_value,
        http_status=result.http_status,
        read_back_value=result.read_back_value,
        rollback_verified=result.rollback_verified,
        duration_ms=result.duration_ms,
        error=result.error,
        steps=result.steps,
        dry_run=dry_run,
    )


@router.post("/sites/{slug}/heartbeat/replay/run", response_model=HeartbeatReplayResponse)
async def run_heartbeat_replay(
    slug: str,
    hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
) -> HeartbeatReplayResponse:
    service = VirtualChargerReplayService(session)
    try:
        report, report_text = await service.run(slug, hours=hours)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Heartbeat replay failed for %s", slug)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return HeartbeatReplayResponse(report=report, report_text=report_text)


@router.get("/sites/{slug}/heartbeat/bridge/commands", response_model=list[dict[str, Any]])
async def list_virtual_charger_commands(
    slug: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    return await repo.list_recent_commands(site.id, limit=limit)


@router.get("/sites/{slug}/heartbeat/bridge/decisions", response_model=list[dict[str, Any]])
async def list_virtual_charger_decisions(
    slug: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    site = await _get_site_or_404(session, slug)
    repo = HeartbeatDiscoveryRepository(session)
    return await repo.list_recent_decisions(site.id, limit=limit)
