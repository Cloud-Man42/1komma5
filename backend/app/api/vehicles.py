"""Vehicle integration API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.deps import get_db_session
from app.schemas import (
    VehicleCapabilitiesResponse,
    VehicleChargeSessionListResponse,
    VehicleChargeSessionResponse,
    VehicleCommandResponse,
    VehicleDetailResponse,
    VehicleIntegrationConfigResponse,
    VehicleIntegrationConfigUpdateRequest,
    VehicleIntegrationLoginResponse,
    VehicleIntegrationStatusResponse,
    VehicleSetTargetSocRequest,
    VehicleUpdateRequest,
    VehicleHaloCorrelationResponse,
    VehicleListItemResponse,
    VehicleListResponse,
    EvEnergySourcesResponse,
)
from energy_core.secrets import SecretBox, SecretBoxError
from energy_core.vehicles.abstractions.models import DataQuality, VehicleConnectionState
from energy_core.vehicles.mercedes.auth.errors import MercedesAuthError, MercedesTwoFactorUnsupported
from energy_core.vehicles.mercedes.auth.login import MercedesLoginFlow
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS
from energy_core.vehicles.mercedes.provider import MercedesProvider
from energy_core.vehicles.vin import mask_vin
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleCapabilityModel, VehicleStateLatestModel
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.commands.errors import VehicleCommandError, VehicleCommandsDisabledError
from energy_core.vehicles.commands.service import VehicleCommandService
from energy_core.db.vehicle_charge_session_repo import VehicleChargeSessionRecord, VehicleChargeSessionRepository
from energy_core.db.repositories import SiteRepository
from sqlalchemy import select

router = APIRouter(tags=["vehicles"])
logger = logging.getLogger(__name__)


async def _site_or_404(session: AsyncSession, slug: str):
    site = await SiteRepository(session).get_by_slug(slug)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _freshness_label(
    *,
    connection_state: str,
    data_quality: str,
    last_vehicle_update: datetime | None,
) -> str:
    if connection_state in {
        VehicleConnectionState.DISCONNECTED.value,
        VehicleConnectionState.BACKOFF.value,
    }:
        return "OFFLINE"
    if data_quality == DataQuality.STALE.value:
        return "INAKTUELL"
    if last_vehicle_update is not None:
        age = (datetime.now(UTC) - last_vehicle_update).total_seconds()
        if age > STALE_TELEMETRY_SECONDS:
            return "INAKTUELL"
    if data_quality in {DataQuality.ESTIMATED.value, DataQuality.CALCULATED.value}:
        return "UPPSKATTAT"
    if data_quality == DataQuality.MEASURED.value:
        return "LIVE"
    return "OFFLINE"


def _correlation_response(record) -> VehicleHaloCorrelationResponse | None:
    if record is None:
        return None
    return VehicleHaloCorrelationResponse(
        charger_id=record.charger_id,
        confidence=record.confidence,
        status=record.status,
        plugged_agreement=record.plugged_agreement,
        charging_agreement=record.charging_agreement,
        power_delta_kw=record.power_delta_kw,
        vehicle_power_kw=record.vehicle_power_kw,
        halo_power_kw=record.halo_power_kw,
        notes=record.notes,
        updated_at=record.updated_at,
    )


def _vehicle_item(
    vehicle,
    latest: VehicleStateLatestModel | None,
    caps: list[VehicleCapabilityModel],
    correlation=None,
) -> VehicleListItemResponse:
    connection_state = latest.connection_state if latest else VehicleConnectionState.DISCONNECTED.value
    data_quality = latest.data_quality if latest else DataQuality.UNKNOWN.value
    return VehicleListItemResponse(
        id=vehicle.id,
        site_id=vehicle.site_id,
        provider=vehicle.provider,
        display_name=vehicle.display_name,
        manufacturer=vehicle.manufacturer,
        model=vehicle.model,
        masked_vin=mask_vin(vehicle.vin) if vehicle.vin else None,
        enabled=vehicle.enabled,
        connection_state=connection_state,
        data_quality=data_quality,
        freshness_label=_freshness_label(
            connection_state=connection_state,
            data_quality=data_quality,
            last_vehicle_update=latest.last_vehicle_update if latest else None,
        ),
        state_of_charge_percent=latest.state_of_charge_percent if latest else None,
        target_soc_percent=latest.target_soc_percent if latest else None,
        electric_range_km=latest.electric_range_km if latest else None,
        is_plugged_in=latest.is_plugged_in if latest else None,
        is_charging=latest.is_charging if latest else None,
        charging_power_kw=latest.charging_power_kw if latest else None,
        last_vehicle_update=latest.last_vehicle_update if latest else None,
        capabilities=VehicleCapabilitiesResponse.from_rows(caps),
        halo_correlation=_correlation_response(correlation),
    )


@router.get("/sites/{slug}/vehicles", response_model=VehicleListResponse)
async def list_vehicles(slug: str, session: AsyncSession = Depends(get_db_session)) -> VehicleListResponse:
    site = await _site_or_404(session, slug)
    vehicles = await VehicleRepository(session).list_for_site(site.id)
    items: list[VehicleListItemResponse] = []
    for vehicle in vehicles:
        latest = await VehicleRepository(session).get_latest_state(vehicle.id)
        caps = (
            await session.execute(
                select(VehicleCapabilityModel).where(VehicleCapabilityModel.vehicle_id == vehicle.id)
            )
        ).scalars().all()
        model = await VehicleRepository(session).get(vehicle.id)
        assert model is not None
        correlation = await VehicleHaloCorrelationRepository(session).get(vehicle.id)
        items.append(_vehicle_item(model, latest, list(caps), correlation))
    return VehicleListResponse(site_slug=slug, vehicles=items)


@router.get("/sites/{slug}/vehicles/{vehicle_id}", response_model=VehicleDetailResponse)
async def get_vehicle(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleDetailResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    latest = await VehicleRepository(session).get_latest_state(vehicle.id)
    caps = (
        await session.execute(select(VehicleCapabilityModel).where(VehicleCapabilityModel.vehicle_id == vehicle.id))
    ).scalars().all()
    item = _vehicle_item(vehicle, latest, list(caps), await VehicleHaloCorrelationRepository(session).get(vehicle.id))
    return VehicleDetailResponse(**item.model_dump(), charger_id=vehicle.charger_id)


@router.patch("/sites/{slug}/vehicles/{vehicle_id}", response_model=VehicleDetailResponse)
async def update_vehicle(
    slug: str,
    vehicle_id: int,
    payload: VehicleUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleDetailResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    repo = VehicleRepository(session)
    if payload.enabled is not None:
        vehicle = await repo.set_enabled(vehicle_id, enabled=payload.enabled)
        assert vehicle is not None
    if payload.display_name is not None:
        vehicle.display_name = payload.display_name.strip() or vehicle.model
    await session.commit()
    latest = await repo.get_latest_state(vehicle.id)
    caps = (
        await session.execute(select(VehicleCapabilityModel).where(VehicleCapabilityModel.vehicle_id == vehicle.id))
    ).scalars().all()
    item = _vehicle_item(vehicle, latest, list(caps), await VehicleHaloCorrelationRepository(session).get(vehicle.id))
    return VehicleDetailResponse(**item.model_dump(), charger_id=vehicle.charger_id)


@router.get("/sites/{slug}/vehicles/{vehicle_id}/halo-correlation", response_model=VehicleHaloCorrelationResponse)
async def get_vehicle_halo_correlation(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleHaloCorrelationResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    record = await VehicleHaloCorrelationRepository(session).get(vehicle_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correlation not available")
    response = _correlation_response(record)
    assert response is not None
    return response


@router.get("/sites/{slug}/vehicles/integration/status", response_model=VehicleIntegrationStatusResponse)
async def get_integration_status(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationStatusResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session)
    row = await repo.get_or_create(site.id)
    record = repo.to_record(row)
    health = "HEALTHY"
    if record.connection_state in {VehicleConnectionState.BACKOFF.value, VehicleConnectionState.DEGRADED.value}:
        health = "DEGRADED"
    if record.connection_state == VehicleConnectionState.DISCONNECTED.value and record.enabled:
        health = "UNHEALTHY"
    if record.blocked_since is not None:
        health = "DEGRADED"
    return VehicleIntegrationStatusResponse(
        site_slug=slug,
        provider=record.provider,
        enabled=record.enabled,
        region=record.region,
        username=record.username,
        password_configured=record.password_configured,
        connection_state=record.connection_state,
        commands_enabled=record.commands_enabled,
        token_expires_at=record.token_expires_at,
        last_error=record.last_error or None,
        last_error_at=record.last_error_at,
        backoff_until=record.backoff_until,
        blocked_since=record.blocked_since,
        reconnect_count=record.reconnect_count,
        http_429_count=record.http_429_count,
        decode_failure_count=record.decode_failure_count,
        health=health,
    )


@router.get("/sites/{slug}/vehicles/integration/config", response_model=VehicleIntegrationConfigResponse)
async def get_integration_config(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationConfigResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session)
    row = await repo.get_or_create(site.id)
    record = repo.to_record(row)
    return VehicleIntegrationConfigResponse(
        site_slug=slug,
        provider=record.provider,
        enabled=record.enabled,
        region=record.region,
        username=record.username,
        password_configured=record.password_configured,
        commands_enabled=record.commands_enabled,
    )


@router.put("/sites/{slug}/vehicles/integration/config", response_model=VehicleIntegrationConfigResponse)
async def update_integration_config(
    slug: str,
    payload: VehicleIntegrationConfigUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationConfigResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session)
    row = await repo.get_or_create(site.id)
    try:
        await repo.update_config(
            row,
            enabled=payload.enabled,
            region=payload.region,
            username=payload.username,
            password=payload.password,
            commands_enabled=payload.commands_enabled,
        )
    except SecretBoxError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    await session.commit()
    record = repo.to_record(row)
    return VehicleIntegrationConfigResponse(
        site_slug=slug,
        provider=record.provider,
        enabled=record.enabled,
        region=record.region,
        username=record.username,
        password_configured=record.password_configured,
        commands_enabled=record.commands_enabled,
    )


@router.post("/sites/{slug}/vehicles/integration/login", response_model=VehicleIntegrationLoginResponse)
async def login_integration(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationLoginResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session)
    row = await repo.get_or_create(site.id)
    if not row.username or not row.encrypted_password:
        raise HTTPException(status_code=422, detail="Username and password must be configured first")
    try:
        password = repo.decrypt_password(row)
    except SecretBoxError as exc:
        raise HTTPException(
            status_code=422,
            detail="Stored Mercedes credentials could not be decrypted. Re-save your password in Config.",
        ) from exc
    provider = MercedesProvider(region=row.region, device_guid=row.device_guid or None)

    async def persist(bundle):
        await repo.persist_token_bundle(row, bundle)

    provider._token_store._persist = persist  # noqa: SLF001
    try:
        bundle = await provider.login(row.username, password)
        await repo.persist_token_bundle(row, bundle)
        await repo.update_runtime_status(row, connection_state=VehicleConnectionState.CONNECTED.value, last_error="")
        await session.commit()
    except MercedesTwoFactorUnsupported as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MercedesAuthError as exc:
        await repo.update_runtime_status(row, connection_state=VehicleConnectionState.BACKOFF.value, last_error=str(exc))
        await session.commit()
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    logger.info("Mercedes authentication successful for site %s", slug)
    return VehicleIntegrationLoginResponse(success=True, message="Mercedes login successful")


def _vehicle_session_response(record: VehicleChargeSessionRecord) -> VehicleChargeSessionResponse:
    return VehicleChargeSessionResponse(
        id=record.id,
        vehicle_id=record.vehicle_id,
        charger_id=record.charger_id,
        connected_at=record.connected_at,
        disconnected_at=record.disconnected_at,
        charging_started_at=record.charging_started_at,
        charging_stopped_at=record.charging_stopped_at,
        start_soc=record.start_soc,
        end_soc=record.end_soc,
        target_soc=record.target_soc,
        status=record.status,
        halo_energy_kwh=record.halo_energy_kwh,
        estimated_battery_energy_delta_kwh=record.estimated_battery_energy_delta_kwh,
        energy_sources=EvEnergySourcesResponse(
            solar_direct_kwh=record.solar_direct_kwh or 0.0,
            solar_battery_kwh=record.solar_battery_kwh or 0.0,
            grid_battery_kwh=record.grid_battery_kwh or 0.0,
            grid_direct_kwh=record.grid_direct_kwh or 0.0,
        ),
        actual_cost_sek=record.actual_cost_sek,
        reference_cost_sek=record.reference_cost_sek,
        savings_sek=record.savings_sek,
        renewable_share_pct=record.renewable_share_pct,
        grid_share_pct=record.grid_share_pct,
        identification_confidence=record.identification_confidence,
        energy_quality=record.energy_quality,
        cost_quality=record.cost_quality,
        attribution_quality=record.attribution_quality,
    )


@router.get(
    "/sites/{slug}/vehicles/{vehicle_id}/charge-sessions",
    response_model=VehicleChargeSessionListResponse,
)
async def list_vehicle_charge_sessions(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleChargeSessionListResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    repo = VehicleChargeSessionRepository(session)
    records = await repo.list_for_vehicle(vehicle_id)
    return VehicleChargeSessionListResponse(
        site_slug=slug,
        vehicle_id=vehicle_id,
        sessions=[_vehicle_session_response(record) for record in records],
    )


@router.get(
    "/sites/{slug}/vehicles/{vehicle_id}/charge-sessions/current",
    response_model=VehicleChargeSessionResponse,
)
async def get_current_vehicle_charge_session(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleChargeSessionResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    record = await VehicleChargeSessionRepository(session).get_current_for_vehicle(vehicle_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return _vehicle_session_response(record)


def _command_http_error(exc: VehicleCommandError) -> HTTPException:
    if isinstance(exc, VehicleCommandsDisabledError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if exc.code in {"vehicle_not_found", "vin_unavailable"}:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if exc.code in {"capability_unavailable", "invalid_target_soc"}:
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if exc.code == "not_authenticated":
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post(
    "/sites/{slug}/vehicles/{vehicle_id}/commands/set-target-soc",
    response_model=VehicleCommandResponse,
)
async def set_vehicle_target_soc(
    slug: str,
    vehicle_id: int,
    payload: VehicleSetTargetSocRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleCommandResponse:
    site = await _site_or_404(session, slug)
    service = VehicleCommandService(session)
    try:
        result = await service.set_target_soc(
            site_id=site.id,
            vehicle_id=vehicle_id,
            target_soc_percent=payload.target_soc_percent,
        )
    except VehicleCommandError as exc:
        raise _command_http_error(exc) from exc
    await session.commit()
    return VehicleCommandResponse(
        success=result.success,
        message=result.message,
        vehicle_id=vehicle_id,
        command=result.command,
    )


@router.post(
    "/sites/{slug}/vehicles/{vehicle_id}/commands/start-charging",
    response_model=VehicleCommandResponse,
)
async def start_vehicle_charging(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleCommandResponse:
    site = await _site_or_404(session, slug)
    service = VehicleCommandService(session)
    try:
        result = await service.start_charging(site_id=site.id, vehicle_id=vehicle_id)
    except VehicleCommandError as exc:
        raise _command_http_error(exc) from exc
    await session.commit()
    return VehicleCommandResponse(
        success=result.success,
        message=result.message,
        vehicle_id=vehicle_id,
        command=result.command,
    )


@router.post(
    "/sites/{slug}/vehicles/{vehicle_id}/commands/stop-charging",
    response_model=VehicleCommandResponse,
)
async def stop_vehicle_charging(
    slug: str,
    vehicle_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleCommandResponse:
    site = await _site_or_404(session, slug)
    service = VehicleCommandService(session)
    try:
        result = await service.stop_charging(site_id=site.id, vehicle_id=vehicle_id)
    except VehicleCommandError as exc:
        raise _command_http_error(exc) from exc
    await session.commit()
    return VehicleCommandResponse(
        success=result.success,
        message=result.message,
        vehicle_id=vehicle_id,
        command=result.command,
    )
