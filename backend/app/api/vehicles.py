"""Vehicle integration API routes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.deps import get_db_session
from app.schemas import (
    VehicleCapabilitiesResponse,
    VehicleChargeSessionListResponse,
    VehicleChargeSessionPatchRequest,
    VehicleChargeSessionResponse,
    VehicleChargingStatsResponse,
    StationCandidateResponse,
    VehicleCommandResponse,
    VehicleDetailResponse,
    VehicleIntegrationConfigResponse,
    VehicleIntegrationConfigUpdateRequest,
    VehicleIntegrationLoginResponse,
    VehicleIntegrationStatusResponse,
    VehicleRawAttributesResponse,
    VehicleAttributeObservationResponse,
    VehicleIntegrationDiagnosticsResponse,
    VehicleIntegrationEventResponse,
    VehicleApiEventResponse,
    VehicleIntegrationActionResponse,
    VehicleSetTargetSocRequest,
    VehicleUpdateRequest,
    VehicleHaloCorrelationResponse,
    VehicleListItemResponse,
    VehicleListResponse,
    VehicleSyncResponse,
    VehicleValueResponse,
    EvEnergySourcesResponse,
)
from energy_core.config import get_settings
from energy_core.secrets import SecretBox, SecretBoxError
from energy_core.vehicles.abstractions.models import DataQuality, VehicleConnectionState
from energy_core.vehicles.mercedes.auth.errors import MercedesAuthError, MercedesTwoFactorUnsupported
from energy_core.vehicles.mercedes.auth.login import MercedesLoginFlow
from energy_core.vehicles.mercedes.constants import STALE_TELEMETRY_SECONDS
from energy_core.vehicles.connection_signals import resolve_effective_connection
from energy_core.vehicles.mercedes.provider import MercedesProvider
from energy_core.vehicles.health import MercedesIntegrationHealthService
from energy_core.vehicles.sessions.repair import repair_completed_sessions
from energy_core.vehicles.vin import mask_vin
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.db.models import VehicleCapabilityModel, VehicleStateLatestModel
from energy_core.db.vehicle_repo import VehicleProviderRepository, VehicleRepository
from energy_core.vehicles.correlation.repo import VehicleHaloCorrelationRepository
from energy_core.vehicles.commands.errors import VehicleCommandError, VehicleCommandsDisabledError
from energy_core.vehicles.commands.service import VehicleCommandService
from energy_core.vehicles.sync_service import VehicleSyncError, VehicleSyncService
from energy_core.vehicles.value_envelope import build_timed_value
from energy_core.vehicles.charging_intelligence.statistics import compute_charging_statistics
from energy_core.db.attribute_observation_repo import VehicleAttributeObservationRepository
from energy_core.db.integration_event_repo import VehicleIntegrationEventRepository
from energy_core.db.charging_location_repo import ChargingLocationRepository
from energy_core.db.charging_station_repo import ChargingStationRepository
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


def _field_is_stale(updated_at: datetime | None) -> bool:
    if updated_at is None:
        return True
    age = (datetime.now(UTC) - updated_at).total_seconds()
    return age > STALE_TELEMETRY_SECONDS


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
    if last_vehicle_update is not None:
        age = (datetime.now(UTC) - last_vehicle_update).total_seconds()
        if age > STALE_TELEMETRY_SECONDS:
            return "INAKTUELL"
        if data_quality in {DataQuality.ESTIMATED.value, DataQuality.CALCULATED.value}:
            return "UPPSKATTAT"
        return "LIVE"
    if data_quality == DataQuality.STALE.value:
        return "INAKTUELL"
    if data_quality in {DataQuality.ESTIMATED.value, DataQuality.CALCULATED.value}:
        return "UPPSKATTAT"
    if data_quality == DataQuality.MEASURED.value:
        return "LIVE"
    return "OFFLINE"


def _latest_signal_timestamp(latest: VehicleStateLatestModel | None) -> datetime | None:
    if latest is None:
        return None
    candidates = [
        latest.last_vehicle_update,
        getattr(latest, "soc_updated_at", None),
        getattr(latest, "charging_updated_at", None),
        getattr(latest, "range_updated_at", None),
        getattr(latest, "location_updated_at", None),
    ]
    known = [ts for ts in candidates if ts is not None]
    return max(known) if known else None


def _guard_stale_connection_fields(
    freshness_label: str,
    *,
    is_plugged_in: bool | None,
    is_charging: bool | None,
    charging_power_kw: float | None,
    charging_updated_at: datetime | None = None,
) -> tuple[bool | None, bool | None, float | None]:
    """Do not present plug/charge state from stale telemetry as current fact."""
    if freshness_label not in {"INAKTUELL", "OFFLINE"}:
        return is_plugged_in, is_charging, charging_power_kw
    if charging_updated_at is not None:
        age = (datetime.now(UTC) - charging_updated_at).total_seconds()
        if age <= STALE_TELEMETRY_SECONDS:
            return is_plugged_in, is_charging, charging_power_kw
    return None, None, None


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


def _value_response(
    value: float | bool | str | None,
    *,
    updated_at: datetime | None,
    estimated: bool = False,
) -> VehicleValueResponse | None:
    if value is None and updated_at is None:
        return None
    timed = build_timed_value(value, source_timestamp=updated_at, received_timestamp=updated_at, estimated=estimated)
    return VehicleValueResponse(
        value=timed.value if isinstance(timed.value, (float, bool, str)) or timed.value is None else str(timed.value),
        source_timestamp=timed.source_timestamp,
        received_timestamp=timed.received_timestamp,
        age_seconds=timed.age_seconds,
        quality=timed.quality.value,
    )


def _vehicle_item(
    vehicle,
    latest: VehicleStateLatestModel | None,
    caps: list[VehicleCapabilityModel],
    correlation=None,
) -> VehicleListItemResponse:
    connection_state = latest.connection_state if latest else VehicleConnectionState.DISCONNECTED.value
    data_quality = latest.data_quality if latest else DataQuality.UNKNOWN.value
    freshness_label = _freshness_label(
        connection_state=connection_state,
        data_quality=data_quality,
        last_vehicle_update=_latest_signal_timestamp(latest),
    )
    effective = resolve_effective_connection(
        latest,
        plugged_agreement=getattr(correlation, "plugged_agreement", None) if correlation else None,
    )
    is_plugged_in, is_charging, charging_power_kw = _guard_stale_connection_fields(
        freshness_label,
        is_plugged_in=effective.is_plugged_in,
        is_charging=effective.is_charging,
        charging_power_kw=latest.charging_power_kw if latest else None,
        charging_updated_at=getattr(latest, "charging_updated_at", None) if latest else None,
    )
    soc_updated_at = getattr(latest, "soc_updated_at", None) if latest else None
    range_updated_at = getattr(latest, "range_updated_at", None) if latest else None
    soc = latest.state_of_charge_percent if latest else None
    electric_range_km = latest.electric_range_km if latest else None
    if _field_is_stale(soc_updated_at):
        soc = None
    if _field_is_stale(range_updated_at):
        electric_range_km = None
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
        freshness_label=freshness_label,
        state_of_charge_percent=soc,
        target_soc_percent=latest.target_soc_percent if latest else None,
        electric_range_km=electric_range_km,
        is_plugged_in=is_plugged_in,
        is_charging=is_charging,
        charging_power_kw=charging_power_kw,
        last_vehicle_update=latest.last_vehicle_update if latest else None,
        state_of_charge=_value_response(
            soc,
            updated_at=soc_updated_at or (latest.last_vehicle_update if latest else None),
            estimated=_field_is_stale(soc_updated_at),
        ),
        charging_power=_value_response(
            latest.charging_power_kw if latest else None,
            updated_at=getattr(latest, "charging_updated_at", None) or (latest.last_vehicle_update if latest else None),
        ),
        electric_range=_value_response(
            electric_range_km,
            updated_at=range_updated_at or (latest.last_vehicle_update if latest else None),
            estimated=_field_is_stale(range_updated_at),
        ),
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


def _sync_http_error(exc: VehicleSyncError) -> HTTPException:
    status_code = {
        "integration_disabled": status.HTTP_503_SERVICE_UNAVAILABLE,
        "not_authenticated": status.HTTP_503_SERVICE_UNAVAILABLE,
        "credentials_stale": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "auth_failed": status.HTTP_502_BAD_GATEWAY,
        "no_telemetry": status.HTTP_502_BAD_GATEWAY,
    }.get(exc.code, status.HTTP_502_BAD_GATEWAY)
    return HTTPException(status_code=status_code, detail=str(exc))


@router.post("/sites/{slug}/vehicles/sync", response_model=VehicleSyncResponse)
async def sync_vehicles(slug: str, session: AsyncSession = Depends(get_db_session)) -> VehicleSyncResponse:
    site = await _site_or_404(session, slug)
    service = VehicleSyncService(session, is_sqlite=get_settings().is_sqlite)
    try:
        states = await service.sync_site(site.id)
    except VehicleSyncError as exc:
        raise _sync_http_error(exc) from exc
    await session.commit()
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
    return VehicleSyncResponse(
        site_slug=slug,
        synced_at=datetime.now(UTC),
        vehicles_updated=len(states),
        vehicles=items,
    )


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


@router.get("/sites/{slug}/vehicles/integration/raw-attributes", response_model=VehicleRawAttributesResponse)
async def get_raw_attributes(
    slug: str,
    vehicle_id: int | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleRawAttributesResponse:
    site = await _site_or_404(session, slug)
    settings = get_settings()
    repo = VehicleAttributeObservationRepository(session, is_sqlite=settings.is_sqlite)
    if vehicle_id is not None:
        vehicle = await VehicleRepository(session).get(vehicle_id)
        if vehicle is None or vehicle.site_id != site.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
        observations = await repo.list_for_vehicle(vehicle_id)
        return VehicleRawAttributesResponse(
            site_slug=slug,
            vehicle_id=vehicle_id,
            observations=[
                VehicleAttributeObservationResponse(
                    attribute_name=obs.attribute_name,
                    source=obs.source,
                    value_type=obs.value_type,
                    masked_sample=obs.masked_sample,
                    first_seen_at=obs.first_seen_at,
                    last_seen_at=obs.last_seen_at,
                    sample_count=obs.sample_count,
                )
                for obs in observations
            ],
        )
    site_rows = await repo.list_for_site(site.id)
    return VehicleRawAttributesResponse(
        site_slug=slug,
        observations=[
            VehicleAttributeObservationResponse(
                attribute_name=obs.attribute_name,
                source=obs.source,
                value_type=obs.value_type,
                masked_sample=obs.masked_sample,
                first_seen_at=obs.first_seen_at,
                last_seen_at=obs.last_seen_at,
                sample_count=obs.sample_count,
            )
            for _vehicle_id, obs in site_rows
        ],
    )


@router.get("/sites/{slug}/vehicles/integration/diagnostics", response_model=VehicleIntegrationDiagnosticsResponse)
async def get_integration_diagnostics(
    slug: str,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationDiagnosticsResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session)
    row = await repo.get_or_create(site.id)
    record = repo.to_record(row)
    latest_vehicle_update = None
    soc_updated_at = None
    soc_age_seconds = None
    vehicles = await VehicleRepository(session).list_for_site(site.id)
    if vehicles:
        latest = await VehicleRepository(session).get_latest_state(vehicles[0].id)
        if latest is not None:
            latest_vehicle_update = latest.last_vehicle_update
            soc_updated_at = getattr(latest, "soc_updated_at", None)
            if soc_updated_at is not None:
                soc_age_seconds = (datetime.now(UTC) - soc_updated_at).total_seconds()
    integration_events = await VehicleIntegrationEventRepository(session).list_recent(site_id=site.id, limit=50)
    health = MercedesIntegrationHealthService().evaluate(
        enabled=record.enabled,
        connection_state=record.connection_state,
        last_success_at=record.last_success_at,
        last_failure_at=record.last_failure_at,
        last_vehicle_update=latest_vehicle_update,
        last_token_refresh_at=record.last_token_refresh_at,
        consecutive_failures=record.consecutive_failures,
        last_error_code=record.last_error_code,
        last_latency_ms=record.last_latency_ms,
        blocked_since=record.blocked_since,
        backoff_until=record.backoff_until,
        token_configured=bool(row.encrypted_access_token),
    )
    return VehicleIntegrationDiagnosticsResponse(
        site_slug=slug,
        health_status=health.status.value,
        connection_state=record.connection_state,
        last_success_at=health.last_success_at,
        last_failure_at=health.last_failure_at,
        last_vehicle_update=health.last_vehicle_update,
        last_token_refresh_at=health.last_token_refresh_at,
        consecutive_failures=health.consecutive_failures,
        last_error_code=health.last_error_code,
        last_latency_ms=health.last_latency_ms,
        current_polling_interval_seconds=record.current_polling_interval_seconds,
        vehicle_data_age_seconds=health.vehicle_data_age_seconds,
        api_data_age_seconds=health.api_data_age_seconds,
        soc_updated_at=soc_updated_at,
        soc_age_seconds=soc_age_seconds,
        recent_events=[],
        integration_events=[
            VehicleIntegrationEventResponse(
                id=event.id,
                event_type=event.event_type,
                severity=event.severity,
                message=event.message,
                details_json=event.details_json,
                vehicle_id=event.vehicle_id,
                recorded_at=event.recorded_at,
            )
            for event in integration_events
        ],
    )


@router.get("/sites/{slug}/vehicles/integration/events", response_model=list[VehicleIntegrationEventResponse])
async def list_integration_events(
    slug: str,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
) -> list[VehicleIntegrationEventResponse]:
    site = await _site_or_404(session, slug)
    capped = max(1, min(limit, 200))
    events = await VehicleIntegrationEventRepository(session).list_recent(site_id=site.id, limit=capped)
    return [
        VehicleIntegrationEventResponse(
            id=event.id,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            details_json=event.details_json,
            vehicle_id=event.vehicle_id,
            recorded_at=event.recorded_at,
        )
        for event in events
    ]


@router.post("/sites/{slug}/vehicles/integration/actions/{action}", response_model=VehicleIntegrationActionResponse)
async def run_integration_action(
    slug: str,
    action: str,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleIntegrationActionResponse:
    site = await _site_or_404(session, slug)
    repo = VehicleProviderRepository(session, secret_box=SecretBox.from_settings())
    row = await repo.get_or_create(site.id)
    if action == "reset":
        await repo.update_runtime_status(
            row,
            connection_state=VehicleConnectionState.DISCONNECTED.value,
            last_error="",
            backoff_until=None,
            blocked_since=None,
            consecutive_failures=0,
            last_error_code=None,
        )
        await session.commit()
        return VehicleIntegrationActionResponse(success=True, message="Integration reset")
    if action == "test-connection":
        if not row.enabled:
            raise HTTPException(status_code=400, detail="Integration is disabled")
        return VehicleIntegrationActionResponse(success=True, message="Connection test scheduled")
    if action == "refresh-token":
        bundle = repo.load_token_bundle(row)
        if bundle is None:
            raise HTTPException(status_code=400, detail="Mercedes is not authenticated")
        return VehicleIntegrationActionResponse(success=True, message="Token refresh scheduled")
    if action == "fetch-vehicle-state":
        sync = VehicleSyncService(session, secret_box=SecretBox.from_settings(), is_sqlite=get_settings().is_sqlite)
        try:
            await sync.sync_site(site.id)
        except VehicleSyncError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        await session.commit()
        return VehicleIntegrationActionResponse(success=True, message="Vehicle state fetched")
    raise HTTPException(status_code=404, detail="Unknown action")


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
        location_name=record.location_name,
        charger_operator=record.charger_operator,
        charging_type=record.charging_type,
        home_charging=record.home_charging,
        energy_source=record.energy_source,
        estimated_energy_kwh=record.estimated_energy_kwh,
        charging_cost_sek=record.charging_cost_sek,
        cost_source=record.cost_source,
        detection_confidence=record.detection_confidence,
        identification_method=record.identification_method,
        vehicle_data_quality=record.vehicle_data_quality,
        charging_power_avg_kw=record.charging_power_avg_kw,
        charging_power_max_kw=record.charging_power_max_kw,
        connector_type=record.connector_type,
        station_name=record.station_name,
        station_provider=record.station_provider,
        station_provider_id=record.station_provider_id,
        distance_from_vehicle_m=record.distance_from_vehicle_m,
        station_confidence=record.station_confidence,
        station_resolution_status=record.station_resolution_status,
        station_candidates=[
            StationCandidateResponse(
                score=item.get("score", 0),
                label=item.get("label", ""),
                provider_station_id=item.get("provider_station_id"),
            )
            for item in (record.station_candidates_json or [])
        ],
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
    await repair_completed_sessions(
        session,
        site_id=site.id,
        vehicle_id=vehicle_id,
        settings=get_settings(),
    )
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
    latest = await VehicleRepository(session).get_latest_state(vehicle_id)
    correlation = await VehicleHaloCorrelationRepository(session).get(vehicle_id)
    effective = resolve_effective_connection(
        latest,
        plugged_agreement=getattr(correlation, "plugged_agreement", None) if correlation else None,
    )
    if not effective.is_plugged_in and not effective.is_charging:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session")
    return _vehicle_session_response(record)


@router.patch(
    "/sites/{slug}/vehicles/{vehicle_id}/charge-sessions/{session_id}",
    response_model=VehicleChargeSessionResponse,
)
async def patch_vehicle_charge_session(
    slug: str,
    vehicle_id: int,
    session_id: int,
    payload: VehicleChargeSessionPatchRequest,
    session: AsyncSession = Depends(get_db_session),
) -> VehicleChargeSessionResponse:
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    repo = VehicleChargeSessionRepository(session)
    record = await repo.get_by_id(session_id)
    if record is None or record.vehicle_id != vehicle_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
    updated = await repo.patch_session(session_id, identification_method="MANUAL", **fields)
    assert updated is not None
    station_repo = ChargingStationRepository(session)
    if record.latitude is not None and record.longitude is not None:
        if payload.location_name:
            await ChargingLocationRepository(session).record_observation(
                site_id=site.id,
                latitude=record.latitude,
                longitude=record.longitude,
                radius_m=100,
                location_name=payload.location_name,
                charger_operator=payload.charger_operator,
                charging_type=payload.charging_type,
            )
        if payload.station_provider_id or payload.station_name or payload.charger_operator:
            confirmed = await station_repo.confirm_station(
                provider=payload.station_provider or "CHARGEFINDER",
                provider_station_id=payload.station_provider_id or f"manual-{session_id}",
                operator=payload.charger_operator,
                station_name=payload.station_name or payload.location_name,
                latitude=record.latitude,
                longitude=record.longitude,
                charging_type=payload.charging_type,
            )
            await repo.patch_session(
                session_id,
                charging_station_id=confirmed.id,
                station_provider=confirmed.provider,
                station_provider_id=confirmed.provider_station_id,
                station_name=confirmed.station_name,
                station_resolution_status="OK",
                identification_method="MANUAL",
            )
            updated = await repo.get_by_id(session_id)
            assert updated is not None
    await session.commit()
    return _vehicle_session_response(updated)


@router.get(
    "/sites/{slug}/vehicles/{vehicle_id}/charging-stats",
    response_model=VehicleChargingStatsResponse,
)
async def get_vehicle_charging_stats(
    slug: str,
    vehicle_id: int,
    period: str = "month",
    session: AsyncSession = Depends(get_db_session),
) -> VehicleChargingStatsResponse:
    if period not in {"day", "week", "month", "year"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid period")
    site = await _site_or_404(session, slug)
    vehicle = await VehicleRepository(session).get(vehicle_id)
    if vehicle is None or vehicle.site_id != site.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    stats = await compute_charging_statistics(
        session,
        site_id=site.id,
        vehicle_id=vehicle_id,
        period=period,
    )
    return VehicleChargingStatsResponse(
        site_slug=slug,
        vehicle_id=vehicle_id,
        period=stats.period,
        total_energy_kwh=stats.total_energy_kwh,
        home_energy_kwh=stats.home_energy_kwh,
        away_energy_kwh=stats.away_energy_kwh,
        ac_energy_kwh=stats.ac_energy_kwh,
        dc_energy_kwh=stats.dc_energy_kwh,
        free_energy_kwh=stats.free_energy_kwh,
        paid_energy_kwh=stats.paid_energy_kwh,
        avg_price_sek_kwh=stats.avg_price_sek_kwh,
        total_cost_sek=stats.total_cost_sek,
        savings_vs_public_sek=stats.savings_vs_public_sek,
        solar_share_pct=stats.solar_share_pct,
        grid_share_pct=stats.grid_share_pct,
        session_count=stats.session_count,
    )


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
